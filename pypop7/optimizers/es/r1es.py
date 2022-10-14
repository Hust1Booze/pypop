import numpy as np

from pypop7.optimizers.es.es import ES


class R1ES(ES):
    """Rank-One Evolution Strategy (R1ES).

    .. note:: `R1ES` is a **low-rank** version of `CMA-ES` specifically designed for large-scale black-box optimization
       (LSBBO) by Li and `Zhang <https://tinyurl.com/32hsbx28>`_. It often works well when there is a `dominated` search
       direction embedded in the subspace. For more complex landscapes (e.g., there are multiple promising search
       directions), other LSBBO variants (e.g., `RMES`, `LMCMA`, `LMMAES`) of `CMA-ES` may be more preferred.

    Parameters
    ----------
    problem : dict
              problem arguments with the following common settings (`keys`):
                * 'fitness_function' - objective function to be **minimized** (`func`),
                * 'ndim_problem'     - number of dimensionality (`int`),
                * 'upper_boundary'   - upper boundary of search range (`array_like`),
                * 'lower_boundary'   - lower boundary of search range (`array_like`).
    options : dict
              optimizer options with the following common settings (`keys`):
                * 'max_function_evaluations' - maximum of function evaluations (`int`, default: `np.Inf`),
                * 'max_runtime'              - maximal runtime to be allowed (`float`, default: `np.Inf`),
                * 'seed_rng'                 - seed for random number generation needed to be *explicitly* set (`int`);
              and with the following particular settings (`keys`):
                * 'sigma'         - initial global step-size, aka mutation strength (`float`),
                * 'mean'          - initial (starting) point, aka mean of Gaussian search distribution (`array_like`),

                  * if not given, it will draw a random sample from the uniform distribution whose search range is
                    bounded by `problem['lower_boundary']` and `problem['upper_boundary']`.

                * 'n_individuals' - number of offspring, aka offspring population size (`int`, default:
                  `4 + int(3*np.log(self.ndim_problem))`),
                * 'n_parents'     - number of parents, aka parental population size (`int`, default:
                  `int(self.n_individuals/2)`),
                * 'c_cov'         - learning rate of low-rank covariance matrix adaptation (`float`, default:
                  `1.0/(3.0*np.sqrt(self.ndim_problem) + 5.0)`),
                * 'c'             - learning rate of evolution path update (`float`, default:
                  `2.0/(self.ndim_problem + 7.0)`),
                * 'c_s'           - learning rate of cumulative step-size adaptation (`float`, default: `0.3`),
                * 'q_star'        - baseline of cumulative step-size adaptation (`float`, default: `0.3`)，
                * 'd_sigma'       - delay factor of cumulative step-size adaptation (`float`, default: `1.0`).

    Examples
    --------
    Use the `ES` optimizer `R1ES` to minimize the well-known test function
    `Rosenbrock <http://en.wikipedia.org/wiki/Rosenbrock_function>`_:

    .. code-block:: python
       :linenos:

       >>> import numpy
       >>> from pypop7.benchmarks.base_functions import rosenbrock  # function to be minimized
       >>> from pypop7.optimizers.es.r1es import R1ES
       >>> problem = {'fitness_function': rosenbrock,  # define problem arguments
       ...            'ndim_problem': 2,
       ...            'lower_boundary': -5*numpy.ones((2,)),
       ...            'upper_boundary': 5*numpy.ones((2,))}
       >>> options = {'max_function_evaluations': 5000,  # set optimizer options
       ...            'seed_rng': 2022,
       ...            'mean': 3*numpy.ones((2,)),
       ...            'sigma': 0.1}  # the global step-size may need to be tuned for better performance
       >>> r1es = R1ES(problem, options)  # initialize the optimizer class
       >>> results = r1es.optimize()  # run the optimization process
       >>> # return the number of function evaluations and best-so-far fitness
       >>> print(f"R1ES: {results['n_function_evaluations']}, {results['best_so_far_y']}")
       R1ES: 5000, 0.0011906055009915095

    For its correctness checking of coding, refer to `this code-based repeatability report
    <https://tinyurl.com/2aywpp2p>`_ for more details.

    Attributes
    ----------
    c               : `float`
                      learning rate of evolution path update.
    c_cov           : `float`
                      learning rate of low-rank covariance matrix adaptation.
    c_s             : `float`
                      learning rate of cumulative step-size adaptation.
    d_sigma         : `float`
                      delay factor of cumulative step-size adaptation.
    mean            : `array_like`
                      initial mean of Gaussian search distribution.
    n_individuals   : `int`
                      number of offspring, aka offspring population size.
    n_parents       : `int`
                      number of parents, aka parental population size.
    q_star          : `float`
                      baseline of cumulative step-size adaptation.
    sigma           : `float`
                      final mutation strength.

    References
    ----------
    Li, Z. and Zhang, Q., 2018.
    A simple yet efficient evolution strategy for large-scale black-box optimization.
    IEEE Transactions on Evolutionary Computation, 22(5), pp.637-646.
    https://ieeexplore.ieee.org/abstract/document/8080257
    """
    def __init__(self, problem, options):
        ES.__init__(self, problem, options)
        self.c_cov = options.get('c_cov', 1.0/(3.0*np.sqrt(self.ndim_problem) + 5.0))  # for Line 5 in Algorithm 1
        self.c = options.get('c', 2.0/(self.ndim_problem + 7.0))  # for Line 12 in Algorithm 1 (c_c)
        self.c_s = options.get('c_s', 0.3)  # for Line 15 in Algorithm 1
        self.q_star = options.get('q_star', 0.3)  # for Line 15 in Algorithm 1
        self.d_sigma = options.get('d_sigma', 1.0)  # for Line 16 in Algorithm 1
        self._x_1 = np.sqrt(1.0 - self.c_cov)  # for Line 5 in Algorithm 1
        self._x_2 = np.sqrt(self.c_cov)  # for Line 5 in Algorithm 1
        self._p_1 = 1.0 - self.c  # for Line 12 in Algorithm 1
        self._p_2 = None  # for Line 12 in Algorithm 1
        self._rr = None  # for rank-based success rule (RSR)

    def initialize(self, args=None, is_restart=False):
        self._p_2 = np.sqrt(self.c*(2.0 - self.c)*self._mu_eff)
        self._rr = np.arange(self.n_parents*2) + 1
        x = np.empty((self.n_individuals, self.ndim_problem))  # offspring population
        mean = self._initialize_mean(is_restart)  # mean of Gaussian search distribution
        p = np.zeros((self.ndim_problem,))  # principal search direction
        s = 0.0  # cumulative rank rate
        y = np.tile(self._evaluate_fitness(mean, args), (self.n_individuals,))  # fitness
        return x, mean, p, s, y

    def iterate(self, x=None, mean=None, p=None, y=None, args=None):
        for k in range(self.n_individuals):  # for Line 3 in Algorithm 1
            if self._check_terminations():
                return x, y
            z = self.rng_optimization.standard_normal((self.ndim_problem,))  # for Line 4 in Algorithm 1
            r = self.rng_optimization.standard_normal()  # for Line 4 in Algorithm 1
            # set for Line 5 in Algorithm 1
            x[k] = mean + self.sigma*(self._x_1*z + self._x_2*r*p)
            y[k] = self._evaluate_fitness(x[k], args)
        return x, y

    def _update_distribution(self, x=None, mean=None, p=None, s=None, y=None, y_bak=None):
        order = np.argsort(y)
        y.sort()  # for Line 10 in Algorithm 1
        # set for Line 11 in Algorithm 1
        mean_w = np.zeros((self.ndim_problem,))
        for k in range(self.n_parents):
            mean_w += self._w[k]*x[order[k]]
        p = self._p_1*p + self._p_2*(mean_w - mean)/self.sigma  # for Line 12 in Algorithm 1
        mean = mean_w  # for Line 11 in Algorithm 1
        # set for rank-based adaptation of mutation strength
        r = np.argsort(np.hstack((y_bak[:self.n_parents], y[:self.n_parents])))
        rr = self._rr[r < self.n_parents] - self._rr[r >= self.n_parents]
        q = np.dot(self._w, rr)/self.n_parents  # for Line 14 in Algorithm 1
        s = (1.0 - self.c_s)*s + self.c_s*(q - self.q_star)  # for Line 15 in Algorithm 1
        self.sigma *= np.exp(s/self.d_sigma)  # for Line 16 in Algorithm 1
        return mean, p, s

    def restart_reinitialize(self, args=None, x=None, mean=None, p=None, s=None, y=None, fitness=None):
        if ES.restart_reinitialize(self):
            x, mean, p, s, y = self.initialize(args, True)
            if self.saving_fitness:
                fitness.append(y[0])
            self.d_sigma *= 2.0
            self._print_verbose_info(y)
        return x, mean, p, s, y

    def optimize(self, fitness_function=None, args=None):  # for all generations (iterations)
        fitness = ES.optimize(self, fitness_function)
        x, mean, p, s, y = self.initialize(args)
        if self.saving_fitness:
            fitness.append(y[0])
        self._print_verbose_info(y)
        while True:
            y_bak = np.copy(y)  # for Line 13 in Algorithm 1
            # sample and evaluate offspring population
            x, y = self.iterate(x, mean, p, y, args)
            if self.saving_fitness:
                fitness.extend(y)
            if self._check_terminations():
                break
            mean, p, s = self._update_distribution(x, mean, p, s, y, y_bak)
            self._n_generations += 1
            self._print_verbose_info(y)
            if self.is_restart:
                x, mean, p, s, y = self.restart_reinitialize(args, x, mean, p, s, y, fitness)
        results = self._collect_results(fitness, mean)
        results['p'] = p
        results['s'] = s
        return results
