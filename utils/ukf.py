import numpy as np

class UKF1D:
    """Unscented Kalman Filter for a 1‑D state (random walk model)."""
    def __init__(self, process_noise=0.01, measurement_noise=0.1):
        self.x = 0.0          # state estimate (filtered value)
        self.P = 1.0          # state covariance
        self.Q = process_noise
        self.R = measurement_noise
        self.initialised = False

        # UKF parameters for state dimension L = 1
        self.L = 1
        self.kappa = 0.0
        self.lam = self.kappa   # lambda = kappa (since L=1, no alpha scaling)
        # Weights
        self.Wm = np.full(3, 1.0 / (2.0 * (self.L + self.lam)))  # 3 weights
        self.Wm[0] = self.lam / (self.L + self.lam)
        self.Wc = self.Wm.copy()
        self.Wc[0] += (1 - 0.0**2 + 2.0)  # beta=2 for Gaussian, but we simplify; beta=0 default
        # Actually, the weight for covariance uses the same as Wm often. We'll use standard formula:
        self.Wc = self.Wm.copy()

    def sigma_points(self):
        """Generate 3 sigma points around current mean x and covariance P."""
        sigma = np.zeros(3)
        sigma[0] = self.x
        dist = np.sqrt((self.L + self.lam) * self.P)
        sigma[1] = self.x + dist
        sigma[2] = self.x - dist
        return sigma

    def predict(self):
        # Process model: x_{k+1} = x_k (random walk)
        # We only need to add process noise to covariance
        self.P += self.Q
        # Sigma points remain the same; we don't need to regenerate them now.

    def update(self, measurement):
        if not self.initialised:
            self.x = measurement
            self.initialised = True
            return self.x

        self.predict()
        sigma = self.sigma_points()

        # Transform sigma points through measurement function (identity)
        sigma_z = sigma  # h(x)=x

        # Predicted measurement mean
        z_hat = np.dot(self.Wm, sigma_z)
        # Predicted measurement covariance
        Pz = 0.0
        for i in range(3):
            diff = sigma_z[i] - z_hat
            Pz += self.Wc[i] * diff * diff
        Pz += self.R

        # Cross covariance
        Pxz = 0.0
        for i in range(3):
            Pxz += self.Wc[i] * (sigma[i] - self.x) * (sigma_z[i] - z_hat)

        # Kalman gain
        K = Pxz / Pz

        # Update state and covariance
        self.x += K * (measurement - z_hat)
        self.P -= K * Pz * K

        return self.x