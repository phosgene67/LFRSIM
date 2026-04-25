class PIDController:
    """
    A standalone PID Controller class.
    This can be reused in Pygame simulations or real-world robotics.
    """
    def __init__(self, kp, ki, kd):
        # Gain Constants
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # State Variables
        self.prev_error = 0
        self.integral = 0
        self.last_p_term = 0
        self.last_i_term = 0
        self.last_d_term = 0
        self.last_output = 0
        
    def calculate(self, error, dt=1.0):
        """
        Calculates the steering/control output based on the error.
        :param error: The difference between target and current position.
        :param dt: Time step (default to 1.0 for frame-based simulation).
        :return: The correction value (steering).
        """
        # 1. Proportional term: Immediate correction
        p_term = self.kp * error
        
        # 2. Integral term: Accumulates past error to fix steady-state drift
        # We use 'Windup Guard' to prevent the integral from growing infinitely
        self.integral += error * dt
        self.integral = max(min(self.integral, 10), -10)
        i_term = self.ki * self.integral
        
        # 3. Derivative term: Predicts future error to prevent overshooting
        # It measures the 'slope' of the error change
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        
        # Save current error for the next calculation
        self.prev_error = error
        
        # Total Output
        self.last_p_term = p_term
        self.last_i_term = i_term
        self.last_d_term = d_term
        self.last_output = p_term + i_term + d_term
        return self.last_output

    def reset(self):
        """Clears the memory of the controller."""
        self.prev_error = 0
        self.integral = 0
        self.last_p_term = 0
        self.last_i_term = 0
        self.last_d_term = 0
        self.last_output = 0