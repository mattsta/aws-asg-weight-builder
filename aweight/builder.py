#!/usr/bin/env python3

import pandas as pd
import boto3

from loguru import logger
import datetime
import pathlib
import json


class InstanceWeightsMaker:
    def __init__(
        self,
        arch="arm64",
        cores=4,
        mem=32,
        fix="mem",
        fix_filter="eq",
        region="us-east-1",
    ):
        self.arch = arch.lower()

        assert self.arch in {
            "arm64",
            "x86_64",
        }, f"Arch must be arm64 or x86_64, but you gave: {self.arch}"

        self.cores = cores
        self.mem = mem
        self.fix = fix.lower()

        self.region = region

        # core filter and memory filter
        self.f = fix_filter

        # "lte" is an option just to fill out the feautre set, but
        # it doesn't really make sense to use as a selector since you'll
        # get non-price-optimized outcomes.
        assert self.f in {"gte", "eq", "lte"}

        self.instances = None

    def generate_instances_cache(self):
        today = datetime.datetime.now().date()
        instancesToday = pathlib.Path(f"instances-{self.region}-{today}.json")

        # if cache file for day doesn't exist, create
        if instancesToday.is_file():
            logger.info("Loading instances from cache: {}", instancesToday)
            instances = json.loads(instancesToday.read_text())
        else:
            logger.info("Instance cache not found, creating a new one...")

            # This is just `aws ec2 describe-instance-types` but the actual API
            # never returns all results at once, so we have to use this multi-step
            # paginator process for what is just one command in the CLI version.
            # Also, we aren't filtering on the instance request because we want
            # a full local cache for filtering locally later and not needing
            # to re-run network fetches if we want to change our local selectors
            # during testing every day.
            ec2 = boto3.client("ec2", self.region)
            paginator = ec2.get_paginator("describe_instance_types")

            instances = []
            for i, page in enumerate(paginator.paginate(), start=1):
                logger.info("Fetched instance result page {}", i)
                instances.extend(page["InstanceTypes"])

            with open(instancesToday, "w") as f:
                json.dump(instances, f, indent=4)

        logger.info("[{}] Total instances found: {}", self.region, len(instances))
        self.instances = instances

    def generate_weights(self):
        if not self.instances:
            self.generate_instances_cache()

        logger.info(
            "Generating weights using REGION={} ARCH={} CORES={} MEM={} FIX={} FILTER={}",
            self.region,
            self.arch,
            self.cores,
            self.mem,
            self.fix,
            self.f,
        )

        KEY_CORE = "VCpuInfo.DefaultCores"
        KEY_MEM = "MemoryInfo.SizeInMiB"

        # If requesting fixed memory limit, core count is the weight
        if self.fix.startswith("mem"):
            NORMALIZE_COLUMN = KEY_CORE
            NORMALIZE_BY = self.cores

            # Filter memory by equality (only give EXACLY self.mem by default),
            # but allow cores to be >= core limit.
            cf = "gte"
            mf = self.f
        elif self.fix.startswith("core"):
            # If requesting fixed core count, memory limit is the weight
            NORMALIZE_COLUMN = KEY_MEM
            NORMALIZE_BY = self.mem * 1024

            # Filter cores by equality (only give EXACTLY self.cores by default),
            # but allow memory to be >= memory limit.
            cf = self.f
            mf = "gte"
        else:
            logger.error(
                "Unknown fixed-column specified: {self.fix}, expected 'mem' or 'cores'"
            )
            return

        # load AWS JSON into a frame
        df = pd.json_normalize(self.instances)

        # The "SupportedArchitectures" field is an array even though the array
        # only ever has one item, so we need to turn the array into native fields
        # so we can select them easier.
        # (looks like AWS expected some multi-arch instances originally, but it never
        # happened, so we have a multi-value field for only single-value attributes now)
        df = df.explode("ProcessorInfo.SupportedArchitectures")

        # Use only architectures we want
        df = df[df["ProcessorInfo.SupportedArchitectures"] == self.arch].reset_index(
            drop=True
        )

        if cf == "eq":
            df = df[df[KEY_CORE] == self.cores].reset_index(drop=True)
        elif cf == "gte":
            df = df[df[KEY_CORE] >= self.cores].reset_index(drop=True)
        elif cf == "lte":
            df = df[df[KEY_CORE] <= self.cores].reset_index(drop=True)
        else:
            assert None, "Invalid filter?"

        # Use only memory capacity we want
        if mf == "eq":
            df = df[df[KEY_MEM] == (self.mem * 1024)].reset_index(drop=True)
        elif mf == "gte":
            df = df[df[KEY_MEM] >= (self.mem * 1024)].reset_index(drop=True)
        elif mf == "lte":
            df = df[df[KEY_MEM] <= (self.mem * 1024)].reset_index(drop=True)
        else:
            assert None, "Invalid filter?"

        resultFrame = (
            df["InstanceType VCpuInfo.DefaultCores MemoryInfo.SizeInMiB".split()]
            .sort_values(NORMALIZE_COLUMN)
            .reset_index(drop=True)
        )

        logger.info("Your filtered results:\n{}", resultFrame.to_string())

        # Using .iterrows() instead of .itertuples() because our column names
        # have dots in them and it breaks the tuple access
        # (fields just become _2, _3, etc).
        goodFields = []
        firstWeight = None

        for idx, row in resultFrame.iterrows():
            # Due to how we now pre-filter by minimum quantities, this
            # if block should never trigger anymore.
            if row[NORMALIZE_COLUMN] < NORMALIZE_BY:
                logger.info(
                    "Skipping because below minimum quantity:\n{}", row.to_string()
                )
                continue

            cores = row[KEY_CORE]
            mem = row[KEY_MEM]
            gbs = mem // 1024

            it = f'"{row.InstanceType}"'

            if not firstWeight:
                firstWeight = round(row[NORMALIZE_COLUMN] / NORMALIZE_BY)

            # We use "round()" here because all AWS Instance types aren't power of two divisible,
            # so if our base is 64 GiB, but an instance above it is 122 GiB, we don't want to do
            # 64 // 122 == 1, we want round(64 / 122) == 2.
            # (Same goes for 64 vs. 244 rounding to 4 instead of 3 with floor division)
            goodFields.append(
                f"    {it:<20} = {round(row[NORMALIZE_COLUMN] / NORMALIZE_BY) // firstWeight:<4} # {cores:>3} cores; {gbs:>4} GiB"
            )

        fieldsByFields = "\n".join(goodFields)
        logger.info(
            "Your weights configuration:\n{}",
            f"instance_types = {{\n{fieldsByFields}\n}}",
        )


@logger.catch()
def cmd():
    import fire

    fire.Fire(InstanceWeightsMaker)


if __name__ == "__main__":
    cmd()
