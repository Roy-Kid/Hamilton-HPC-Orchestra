# Hamilton-HPC-Orchestra
[WIP] An extension for sf-hamilton to delegate node/task to HPC resource management system

## Proposal
[Hamilton](https://hamilton.dagworks.io/en/latest/) is a general-purpose, extensible workflow framework with high-quality code. The data flow or workflow is constructed using pure Python functions, which are compiled into a DAG (Directed Acyclic Graph) and executed by different executors. To scale up the Python code for parallel and remote execution, several [GraphAdapters](https://hamilton.dagworks.io/en/latest/reference/graph-adapters/) have been implemented. These extensions allow pure Python code to be orchestrated with third-party unified compute frameworks, such as Ray, Dask, Spark, etc.

However, in traditional computational scientific fields, we still rely on classic resource management systems, such as [SLURM](https://slurm.schedmd.com/documentation.html) and [PBS](https://www.pbs.org/). It is sometimes even difficult to use Docker and install your technology stack due to limited storage and file number quotas. Thus, a lightweight "submitter" needs to be implemented to interact with resource management systems. 

Another requirement is that research groups often have more than one cluster. These clusters are distributed across different regions and run on different operating systems. Researchers need to manually balance the load, determining which task should be submitted to which cluster, and they also need to check the status by logging into different clusters. This process becomes quite tedious when the number of tasks surges.

Hereby, after many experiments, we propose a new protocol for fine-grained control task submission in Hamilton workflow:
```python
@submit(system_alias, system_type, [option])
def task_to_submite(upstream: Any) -> Generator[dict, CompletedProcess, Any]:
    # before submit
    job_info: JobInfo = yield dict(
        name: str,
        max_cores: str,
        partition: str,
        ... # other config
        dependency: job_info,
        monitor: bool,  # if block until finished
    )
    # after submit
    return result
```
This protocol is non-invasive and can control resources at the node/task level. For example, small or short-time tasks can be assigned to a cluster with few queues but limited runtime, while long-duration tasks can be assigned to machines with long-duration nodes.

These resource management systems are similar; they all use bash scripts with directives. However, the keywords and formats are slightly different. Therefore, we use [a uniform alias/keyword](https://github.com/pyiron/pysqa) for disambiguation.

Another external task is we need to execute non-python program such as using `subprocessing.run`. Those tasks is very similar with submit job, although run locally. The subsequent tasks reply on the result / files generated by commandline programm. We may execute it in such way:

```python
@cmdline
def execute_cmdline(upstream: Any) -> Generator[dict, CompletedProcess, str]:
    # before execution
    result: CompletedProcess = yield dict(
      'cmd': ['echo', 'something'],
      'block': True
    )
    # after execution
    # return anything, lets say str
    return result.stdout.decode().strip()
```
we can find those two decorator share same patter: 

``` python
@do_external_stuff
def foo(Any) -> Generator[dict, Any, Any]

    result_from_external: Any = yield dict_config

    # inside yield, we need to:
    #   - check decorated func is generator
    #   - copy signature and doc to new one
    #   - validate config
    #   - execute
    #   - send result back
    #   - extra check
    # pesudo code:
    ```
    def __call__(self, func: Callable):

        if not isgeneratorfunction(func):
            raise TypeError(f"Function {func.__name__} must be a generator function")

        func = self.modify_function(func)

        @wraps(func)
        def wrapper(*args, **kwargs):

            generator = func(*args, **kwargs)
            config: dict = next(generator)
            config = self.validate_config(config)

            # do something
            result = self.do(config)

            try:
                generator.send(result)
                # ValueError should not be hit because a StopIteration should be raised, unless
                # there are multiple yields in the generator.
                raise ValueError("Generator cannot have multiple yields.")
            except StopIteration as e:
                result = e.value

            return result

        # get the return type and set it as the return type of the wrapper
        wrapper.__annotations__["return"] = signature(func).return_annotation
        return wrapper
    ```
    return result
```

Between these two APIs, I abstract a new `YieldDecorator` abstract class. To extend it, just implement `self.do` and `self.valid_config` methods. Sometime we need to tag the function internally. For `CMDLineExecutionManager`, it checks the tag `cmdline` on the node and decide which executor it should use. So I provide another api called `self.modify_function` to tag function: `def modify_func(func)->tag(cmdline=true)(func)`.

## TODO list

- [x] abstract submitor
- [x] implement local submitor ("submit" with bash for testing)
- [x] implement slurm submitor
- [x] abstract Yield-like decorator
- [x] refactor `@cmdline` with abstract decorator
- [x] refactor `@submit` with abstract decorator
- [x] config validator

- [x] tag cached node: 
        if not tag it, when cache it the function will return result instead of config dict
        potential solution: tag it in `run_after_node_execution`
        if detect it's cached, skip submit:
        ```python
        generator = func(*args, **kwargs)
        if generator has tag:
            return generator
        config: dict = next(generator)
        ```
- [ ] not compatible with `@inject`:
        RuntimeError: Error running task md_eq: module, class, method, function, traceback, frame, or code object was expected, got partial