import numpy as np

from pypop7.optimizers.core.optimizer import Optimizer


class DS(Optimizer):
    """Direct Search (DS).

    This is the **base** class for all DS classes.

    .. note:: Its three methods (`initialize`, `iterate`, `optimize`) should be implemented by
       its subclass.

    Parameters
    ----------
    problem : dict
              problem arguments.
    options : dict
              optimizer options.

    Attributes
    ----------
    x     : `array_like`
            initial (starting) point.
    sigma : float
            initial (global) step-size.

    Methods
    -------

    References
    ----------
    Kochenderfer, M.J. and Wheeler, T.A., 2019.
    Algorithms for optimization. MIT Press.
    https://algorithmsbook.com/optimization/
    (See Chapter 7: Direct Methods for details.)

    Audet, C. and Hare, W., 2017. Derivative-free and blackbox optimization.
    Berlin: Springer International Publishing.
    https://link.springer.com/book/10.1007/978-3-319-68913-5

    Torczon, V., 1997.
    On the convergence of pattern search algorithms.
    SIAM Journal on Optimization, 7(1), pp.1-25.
    https://epubs.siam.org/doi/abs/10.1137/S1052623493250780

    `Wright, M.H. <https://www.informs.org/Explore/History-of-O.R.-Excellence/Biographical-Profiles/Wright-Margaret-H>`_
    , 1996. Direct search methods: Once scorned, now respectable.
    Pitman Research Notes in Mathematics Series, pp.191-208.
    https://nyuscholars.nyu.edu/en/publications/direct-search-methods-once-scorned-now-respectable

    Nelder, J.A. and Mead, R., 1965.
    A simplex method for function minimization.
    The Computer Journal, 7(4), pp.308-313.
    https://academic.oup.com/comjnl/article-abstract/7/4/308/354237

    Hooke, R. and Jeeves, T.A., 1961.
    “Direct search” solution of numerical and statistical problems.
    Journal of the ACM, 8(2), pp.212-229.
    https://dl.acm.org/doi/10.1145/321062.321069

    Fermi, E. and Metropolis N., 1952.
    Numerical solution of a minimum problem.
    Los Alamos Scientific Lab., Los Alamos, NM.
    https://www.osti.gov/servlets/purl/4377177
    """
    def __init__(self, problem, options):
        """Initialize the parameter settings of the DS class.

        Parameters
        ----------
        problem : dict
                  problem arguments.
        options : dict
                  optimizer options.
        """
        Optimizer.__init__(self, problem, options)
        self.x = options.get('x')  # initial (starting) point
        self.sigma = options.get('sigma')  # initial (global) step-size
        self._n_generations = 0  # number of generations
        # for restart
        self.n_restart = 0  # number of restarts
        self.sigma_threshold = options.get('sigma_threshold', 1e-10)  # stopping threshold of sigma for restart
        # maximal generation number of fitness stagnation for restart
        self.stagnation = options.get('stagnation', np.maximum(32, self.ndim_problem))
        self.fitness_diff = options.get('fitness_diff', 1e-10)  # stopping threshold of fitness difference for restart
        self._sigma_bak = np.copy(self.sigma)  # bak for restart
        self._fitness_list = [self.best_so_far_y]  # to store `best_so_far_y` generated in each generation

    def initialize(self):
        raise NotImplementedError

    def iterate(self):
        raise NotImplementedError

    def _initialize_x(self, is_restart=False):
        if is_restart or (self.x is None):
            x = self.rng_initialization.uniform(self.initial_lower_boundary, self.initial_upper_boundary)
        else:
            x = np.copy(self.x)
        return x

    def _print_verbose_info(self, y):
        if self.verbose and (not self._n_generations % self.verbose_frequency):
            info = '  * Generation {:d}: best_so_far_y {:7.5e}, min(y) {:7.5e} & Evaluations {:d}'
            print(info.format(self._n_generations, self.best_so_far_y, np.min(y), self.n_function_evaluations))

    def _collect_results(self, fitness):
        results = Optimizer._collect_results(self, fitness)
        results['sigma'] = self.sigma
        results['n_restart'] = self.n_restart
        results['_n_generations'] = self._n_generations
        return results
