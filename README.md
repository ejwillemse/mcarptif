# MCARPTIF

This repo contains implementations of heuristics to deal with the Mixed Capacitated Arc Routing Problem under Time restrictions with Intermediate Facilities. The problem is directly relevant to waste collection where a fleet of homogeneous vehicles have to collect waste on streets. Collection routes have to be completed within a certain period, typically corresponding to an 8-hour work day. Vehicles are allowed to unload their waste at intermediate-facilities once they reach capacity. The problem further accounts for mixed-road networks with one and two way streets.

For more information on the problem, see:

* <http://hdl.handle.net/2263/57510>: the thesis contains all the technical details

And there are these publications:

* <https://doi.org/10.1016/j.cor.2015.10.010>: details on the constructive heuristics
* <https://doi.org/10.1016/j.orl.2016.06.001>: details on a splitting procedure used in the constructive heuristics
* <https://doi.org/10.1016/j.dib.2016.06.067>: details on the benchmark instances solved
* <https://doi.org/10.1016/j.cor.2019.02.002>: details on the improvement procedure.

They are all available from <https://www.researchgate.net/profile/Elias_Willemse>.

**Keywords:** Capacitated Arc Routing Problem, mixed-networks, intermediate facilities, heuristics, metaheuristics.

## Setup

The algorithms can be run in Python 3. I recommend setting up a virtual environment via `pip`. Dependencies are available from: `requirements.txt`.

The easiest way to get started is via command-line/terminal. Just navigate to where you cloned this repo and do the following.

First, setup a virtual environment:

```
$ python3 -m venv .venv
```

This will create a `.venv/` folder which should not be committed (it's already been added to `.gitignore`). Next, activate it (note that the command starts with `. `):

```
$ . .venv/bin/activate
```

You should see a `(.venv)` somewhere in the beginning of the terminal line.

Next, install all the dependencies

``` 
$ pip install -r requirements.txt
```

The code requires `Cython 0.29.14`, which compiles some of the critical algorithm components into C. For this, you will need a c-compiler (though the errors will only pop-up later).

Next, activate a python session.

```
$ python
```

There are a bunch of benchmark problems under `data/`, including a test file `data/Lpr_IF-c-03_test.txt`. You can use it to check if everything is working ok.

```
>>> from solver import solve_store_instance
```

All the code will compile, including the c-extensions. If you are getting funny `gcc` errors, chances are your c-compiler is not setup. On MacOX, you need to install XCode. [This post](https://github.com/cython/cython/wiki/CythonExtensionsOnWindows) may help on Windows.

Assuming the file loaded correctly, you can solve the instance:

```
>>> solve_store_instance('data/Lpr_IF-c-03_test.txt')
.
.
.
Saving converted data files to `data/`
Writing encoded solution to data/Lpr_IF-c-03_test_sol_ps.csv
Writing full solution to data/Lpr_IF-c-03_test_sol_full_ps.csv
```

This will create a solution file `data/Lpr_IF-c-03_test_sol_full_ps.csv` that you can view with any text editor or programme that can deal with csv's (Excel, R, basic text editor, etc).

To use a more advanced local search, but slower solution technique:

```
>>> solve_store_instance('data/Lpr_IF-c-03_test.txt', improve = 'LS')
.
.
.
Writing encoded solution to data/Lpr_IF-c-03_test_sol_ps_local_search.csv
Writing full solution to data/Lpr_IF-c-03_test_sol_full_ps_local_search.csv
```

To use a tabu-search metaheuristics which is better but even slower since we are dealing with a medium size instance:

```
>>> solve_store_instance('data/Lpr_IF-c-03_test.txt', improve = 'TS')
.
.
.
Initial and incumbent cost: 111921 	 114908
Initial and incumbent fleet size: 4 	 4

Writing encoded solution to data/Lpr_IF-c-03_test_sol_ps_tabu_search.csv
Writing full solution to data/Lpr_IF-c-03_test_sol_full_ps_tabu_search.csv
```

The solution module and description of the output file is pretty well documented in the `solve_store_instance` module. Just run:

```
>>> help(solve_store_instance)
```

or check-out the module directly in `solver/solve/solve.py` (it's the last module).

## Real application

It would be great if someone wishes to use this for real route planning (check the license--- basically, you can do whatever you want, except hold me liable when things go wrong). From our experience, the biggest issue is not developing the routes, it's getting the input data required for these algorithms. The following information is required:

1. Vehicle capacity.
2. Work duration limits.
3. Full-connected network of the service area with the normal travel speed of the vehicles through each road segment, and the service time of the vehicle for each segment with waste.
4. Quantity of waste to be collected on road segments that have to be serviced.
5. Network location of dumpsite, landfills or intermediate facilities, and the depot.
6. Time required to offload waste.

Points 3 and 4 are a tall order for most municipalities. The street network can be collected from OSM, but thereafter it has to be split into road segments and then converted into the correct format for these algorithms. We've hacked our way through this a few times, but unfortunately we have nothing to automate this process.

The speed and waste quantities are a really tricky one. We've been working on a way to use GPS records of the vehicle fleet, which could also be linked to weigh-bridge data. It's a simple process. See [this post](https://www.linkedin.com/pulse/using-data-science-analyse-waste-collection-willemse-phd-pr-eng-/) for some preliminary results.

## Questions

Feel free to create issues or drop me an email at ejwillemse gmail
