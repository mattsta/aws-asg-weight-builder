AWS EC2 Auto Scaling Group Weight Builder
=========================================


[AWS EC2 ASGs](https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html) allow you to define
a collection of allowable instance types to use for automatic scaling operations (so your deployed instance counts can grow and shrink automatically).


You can configure ASG launch templates to use [multiple instance types allocated by weight](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-mixed-instances-groups-instance-weighting.html) then the AWS EC2 ASG will pick the best price-vs-weight-vs-capacity tradeoff automatically for you.

Using AWS EC2 ASG with a heavily customized Launch Template specifying all instances capable of running your workload gives you the most price-vs-uptime flexibility when using SPOT instances as well. If you can specify the top 40 instance types in your spot pools capable of running your workloads, you can potentially run your service on full time spot instances with auto-restart and auto-redeploy without wasting money on full price instances.

Unfortunately, the art of actually creating a proper weights configuration for AWS EC2 ASG configurations is combinations of annoying, difficult, and time consuming because:

- AWS now has almost 500 instance types (with different availability by region)
- ASG instance type weights must be configured in perhaps non-intuitive ways if you don't want scaling to be slow or fail completely
- You must realize weights need to always start at 1 when using AWS EC2 ASG as ECS capacity provider or else the ECS->ASG auto scale logic won't work correctly.


## Usage

```bash

pip install poetry -U

git clone https://github.com/mattsta/aws-asg-weight-builder
cd aws-asg-weight-builder

poetry install
poetry run build-weights --arch=x86_64 --fix=mem --cores=4 --mem=32 --fix_filter=eq - generate_weights
poetry run build-weights --arch=arm64 --fix=cores --cores=8 --mem=32 --fix_filter=gte - generate_weights
```

## Arguments

`aws-asg-weight-builder` is a command line app taking the following parameters:

```haskell
FLAGS
    --arch=ARCH
        Default: 'arm64'
    --cores=CORES
        Default: 4
    --mem=MEM
        Default: 32
    --fix=FIX
        Default: 'mem'
    --fix_filter=FIX_FILTER
        Default: 'eq'
    --region=REGION
        Default: 'us-east-1'
```

### Argument Description


#### --arch={arm64,x86_64}

Pick your required instance architecture.

### --cores=N

Pick your number of physical cores required.

Can be flexibly adjusted via the `--fix_filter` parameter when `--fix=cores`

### --mem=N (in GiB)

Pick your GiB required capacity.

Can be flexibly adjusted via the `--fix_filter` parameter when `--fix=memory`


### --fix={cores,memory}

Since the instance weights have two dimensions for our selection of cores/memory, you need to
specify which is the correct filter value (cores or memory) then the other value is allowed
to float higher than the given value for maximum flexibility.

Note: your calculated weights are the OPPOSITE of the `fix` condition. If you fix by `cores`, your weights are by `memory`,
and if you fix by `memory`, your weights are by multiples of `cores`.

### --fix_filter={eq,gte}

If fix=cores and cores=N and filter=eq and mem=Y, ONLY return instances with cores==N but memory is allowed to be >= Y.

If fix=memory and cores=N and filter=eq and mem=Y, ONLY return instances with memory==Y, but cores are allowed to be >= N.

If fix=cores and cores=N and filter=gte and mem=Y, ONLY return instances with cores >= N but memory is allowed to be >= Y.

If fix=memory and cores=N and filter=gte and mem=Y, ONLY return instances with memory >= Y, but cores are allowed to be >= N.


## Sample Output

### `poetry run build-weights --arch=arm64 --fix=cores --cores=8 --mem=32 --fix_filter=gte - generate_weights`

Builds weights for:

- `arm64` instances only
- select fixed selection by `cores`, plus allow `cores` filter to be `gte` (`>=`) the requested number
    - because `fix` is `cores`, the weights are allocated by MEMORY multiples from the starting amount
- with `cores` count `gte` `8` (note: this is physical cores not `vCPU`)
- with `memory` starting at `32 GiB`

Results are the results of filtering the near-500 instance list plus auto-weighting by your selection criteria.

```haskell
aweight.builder:generate_instances_cache:51 - Loading instances from cache: instances-us-east-1-2022-01-29.json
aweight.builder:generate_instances_cache:74 - [us-east-1] Total instances found: 474
aweight.builder:generate_weights:81 - Generating weights using REGION=us-east-1 ARCH=arm64 CORES=8 MEM=32 FIX=cores FILTER=gte
aweight.builder:generate_weights:158 - Your filtered results:
      InstanceType  VCpuInfo.DefaultCores  MemoryInfo.SizeInMiB
0     m6gd.2xlarge                      8                 32768
1      c6g.4xlarge                     16                 32768
2     c6gn.4xlarge                     16                 32768
3      t4g.2xlarge                      8                 32768
4         a1.metal                     16                 32768
5     c6gd.4xlarge                     16                 32768
6      m6g.2xlarge                      8                 32768
7    im4gn.2xlarge                      8                 32768
8       a1.4xlarge                     16                 32768
9      g5g.4xlarge                     16                 32768
10  is4gen.2xlarge                      8                 49152
11     c6g.8xlarge                     32                 65536
12   im4gn.4xlarge                     16                 65536
13    m6gd.4xlarge                     16                 65536
14    c6gd.8xlarge                     32                 65536
15    c6gn.8xlarge                     32                 65536
16    r6gd.2xlarge                      8                 65536
17     r6g.2xlarge                      8                 65536
18     m6g.4xlarge                     16                 65536
19     g5g.8xlarge                     32                 65536
20   c6gd.12xlarge                     48                 98304
21    c6g.12xlarge                     48                 98304
22  is4gen.4xlarge                     16                 98304
23   c6gn.12xlarge                     48                 98304
24       g5g.metal                     64                131072
25    x2gd.2xlarge                      8                131072
26    r6gd.4xlarge                     16                131072
27     m6g.8xlarge                     32                131072
28    c6g.16xlarge                     64                131072
29   im4gn.8xlarge                     32                131072
30    g5g.16xlarge                     64                131072
31     r6g.4xlarge                     16                131072
32   c6gd.16xlarge                     64                131072
33   c6gn.16xlarge                     64                131072
34      c6gd.metal                     64                131072
35       c6g.metal                     64                131072
36    m6gd.8xlarge                     32                131072
37  is4gen.8xlarge                     32                196608
38    m6g.12xlarge                     48                196608
39   m6gd.12xlarge                     48                196608
40    r6gd.8xlarge                     32                262144
41     r6g.8xlarge                     32                262144
42  im4gn.16xlarge                     64                262144
43      m6gd.metal                     64                262144
44   m6gd.16xlarge                     64                262144
45    m6g.16xlarge                     64                262144
46    x2gd.4xlarge                     16                262144
47       m6g.metal                     64                262144
48   r6gd.12xlarge                     48                393216
49    r6g.12xlarge                     48                393216
50       r6g.metal                     64                524288
51    r6g.16xlarge                     64                524288
52    x2gd.8xlarge                     32                524288
53      r6gd.metal                     64                524288
54   r6gd.16xlarge                     64                524288
55   x2gd.12xlarge                     48                786432
56   x2gd.16xlarge                     64               1048576
57      x2gd.metal                     64               1048576
aweight.builder:generate_weights:193 - Your weights configuration:
instance_types = {
    "m6gd.2xlarge"       = 1    #   8 cores;   32 GiB
    "c6g.4xlarge"        = 1    #  16 cores;   32 GiB
    "c6gn.4xlarge"       = 1    #  16 cores;   32 GiB
    "t4g.2xlarge"        = 1    #   8 cores;   32 GiB
    "a1.metal"           = 1    #  16 cores;   32 GiB
    "c6gd.4xlarge"       = 1    #  16 cores;   32 GiB
    "m6g.2xlarge"        = 1    #   8 cores;   32 GiB
    "im4gn.2xlarge"      = 1    #   8 cores;   32 GiB
    "a1.4xlarge"         = 1    #  16 cores;   32 GiB
    "g5g.4xlarge"        = 1    #  16 cores;   32 GiB
    "is4gen.2xlarge"     = 2    #   8 cores;   48 GiB
    "c6g.8xlarge"        = 2    #  32 cores;   64 GiB
    "im4gn.4xlarge"      = 2    #  16 cores;   64 GiB
    "m6gd.4xlarge"       = 2    #  16 cores;   64 GiB
    "c6gd.8xlarge"       = 2    #  32 cores;   64 GiB
    "c6gn.8xlarge"       = 2    #  32 cores;   64 GiB
    "r6gd.2xlarge"       = 2    #   8 cores;   64 GiB
    "r6g.2xlarge"        = 2    #   8 cores;   64 GiB
    "m6g.4xlarge"        = 2    #  16 cores;   64 GiB
    "g5g.8xlarge"        = 2    #  32 cores;   64 GiB
    "c6gd.12xlarge"      = 3    #  48 cores;   96 GiB
    "c6g.12xlarge"       = 3    #  48 cores;   96 GiB
    "is4gen.4xlarge"     = 3    #  16 cores;   96 GiB
    "c6gn.12xlarge"      = 3    #  48 cores;   96 GiB
    "g5g.metal"          = 4    #  64 cores;  128 GiB
    "x2gd.2xlarge"       = 4    #   8 cores;  128 GiB
    "r6gd.4xlarge"       = 4    #  16 cores;  128 GiB
    "m6g.8xlarge"        = 4    #  32 cores;  128 GiB
    "c6g.16xlarge"       = 4    #  64 cores;  128 GiB
    "im4gn.8xlarge"      = 4    #  32 cores;  128 GiB
    "g5g.16xlarge"       = 4    #  64 cores;  128 GiB
    "r6g.4xlarge"        = 4    #  16 cores;  128 GiB
    "c6gd.16xlarge"      = 4    #  64 cores;  128 GiB
    "c6gn.16xlarge"      = 4    #  64 cores;  128 GiB
    "c6gd.metal"         = 4    #  64 cores;  128 GiB
    "c6g.metal"          = 4    #  64 cores;  128 GiB
    "m6gd.8xlarge"       = 4    #  32 cores;  128 GiB
    "is4gen.8xlarge"     = 6    #  32 cores;  192 GiB
    "m6g.12xlarge"       = 6    #  48 cores;  192 GiB
    "m6gd.12xlarge"      = 6    #  48 cores;  192 GiB
    "r6gd.8xlarge"       = 8    #  32 cores;  256 GiB
    "r6g.8xlarge"        = 8    #  32 cores;  256 GiB
    "im4gn.16xlarge"     = 8    #  64 cores;  256 GiB
    "m6gd.metal"         = 8    #  64 cores;  256 GiB
    "m6gd.16xlarge"      = 8    #  64 cores;  256 GiB
    "m6g.16xlarge"       = 8    #  64 cores;  256 GiB
    "x2gd.4xlarge"       = 8    #  16 cores;  256 GiB
    "m6g.metal"          = 8    #  64 cores;  256 GiB
    "r6gd.12xlarge"      = 12   #  48 cores;  384 GiB
    "r6g.12xlarge"       = 12   #  48 cores;  384 GiB
    "r6g.metal"          = 16   #  64 cores;  512 GiB
    "r6g.16xlarge"       = 16   #  64 cores;  512 GiB
    "x2gd.8xlarge"       = 16   #  32 cores;  512 GiB
    "r6gd.metal"         = 16   #  64 cores;  512 GiB
    "r6gd.16xlarge"      = 16   #  64 cores;  512 GiB
    "x2gd.12xlarge"      = 24   #  48 cores;  768 GiB
    "x2gd.16xlarge"      = 32   #  64 cores; 1024 GiB
    "x2gd.metal"         = 32   #  64 cores; 1024 GiB
}
```


### `poetry run build-weights --arch=x86_64 --fix=mem --cores=4 --mem=32 --fix_filter=eq - generate_weights`

Builds weights for:

- `x86_64` instances only
- select fixed selection by `memory`, plus allow `memory` filter to strictly `eq` (`==`) so ONLY return EXACTLY memory limit
    - because `fix` is `memory`, the weights are allocated by CORE multiples from the starting amount
- with `cores` count minimum `4` (note: this is physical cores not `vCPU`)
- with `memory` fixed to the `eq` value of `32 GiB`

Results are the results of filtering the near-500 instance list plus auto-weighting by your selection criteria.

```haskell
aweight.builder:generate_instances_cache:51 - Loading instances from cache: instances-us-east-1-2022-01-29.json
aweight.builder:generate_instances_cache:74 - [us-east-1] Total instances found: 474
aweight.builder:generate_weights:81 - Generating weights using REGION=us-east-1 ARCH=x86_64 CORES=4 MEM=32 FIX=mem FILTER=eq
aweight.builder:generate_weights:158 - Your filtered results:
    InstanceType  VCpuInfo.DefaultCores  MemoryInfo.SizeInMiB
0   m5dn.2xlarge                      4                 32768
1    m5d.2xlarge                      4                 32768
2    m5n.2xlarge                      4                 32768
3     m5.2xlarge                      4                 32768
4     m4.2xlarge                      4                 32768
5     h1.2xlarge                      4                 32768
6   g4ad.2xlarge                      4                 32768
7   m5ad.2xlarge                      4                 32768
8    m6i.2xlarge                      4                 32768
9   g4dn.2xlarge                      4                 32768
10  m5zn.2xlarge                      4                 32768
11   m6a.2xlarge                      4                 32768
12   t3a.2xlarge                      4                 32768
13    t3.2xlarge                      4                 32768
14    g5.2xlarge                      4                 32768
15   m5a.2xlarge                      4                 32768
16  d3en.2xlarge                      4                 32768
17    t2.2xlarge                      8                 32768
18   c5a.4xlarge                      8                 32768
19  c5ad.4xlarge                      8                 32768
20   c5d.4xlarge                      8                 32768
21   c6i.4xlarge                      8                 32768
22    c5.4xlarge                      8                 32768
aweight.builder:generate_weights:193 - Your weights configuration:
instance_types = {
    "m5dn.2xlarge"       = 1    #   4 cores;   32 GiB
    "m5d.2xlarge"        = 1    #   4 cores;   32 GiB
    "m5n.2xlarge"        = 1    #   4 cores;   32 GiB
    "m5.2xlarge"         = 1    #   4 cores;   32 GiB
    "m4.2xlarge"         = 1    #   4 cores;   32 GiB
    "h1.2xlarge"         = 1    #   4 cores;   32 GiB
    "g4ad.2xlarge"       = 1    #   4 cores;   32 GiB
    "m5ad.2xlarge"       = 1    #   4 cores;   32 GiB
    "m6i.2xlarge"        = 1    #   4 cores;   32 GiB
    "g4dn.2xlarge"       = 1    #   4 cores;   32 GiB
    "m5zn.2xlarge"       = 1    #   4 cores;   32 GiB
    "m6a.2xlarge"        = 1    #   4 cores;   32 GiB
    "t3a.2xlarge"        = 1    #   4 cores;   32 GiB
    "t3.2xlarge"         = 1    #   4 cores;   32 GiB
    "g5.2xlarge"         = 1    #   4 cores;   32 GiB
    "m5a.2xlarge"        = 1    #   4 cores;   32 GiB
    "d3en.2xlarge"       = 1    #   4 cores;   32 GiB
    "t2.2xlarge"         = 2    #   8 cores;   32 GiB
    "c5a.4xlarge"        = 2    #   8 cores;   32 GiB
    "c5ad.4xlarge"       = 2    #   8 cores;   32 GiB
    "c5d.4xlarge"        = 2    #   8 cores;   32 GiB
    "c6i.4xlarge"        = 2    #   8 cores;   32 GiB
    "c5.4xlarge"         = 2    #   8 cores;   32 GiB
}
```
