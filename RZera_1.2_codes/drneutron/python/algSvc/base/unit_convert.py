from drneutron.python.utils.constants import *

class UnitConverter:
    def __init__(self, flight_distance,theta):
        self.h_m_n = h_planck/neutron_mass*10e3#convert unit to us and AA
        self.flight_distance = flight_distance
        self.theta = theta
        self.units={"dspacing":"A","tof":"us","wavelength":"A","q":"AA","energy":"meV"}

    def tof_to_velocity(self, time_of_flight):
        return self.flight_distance / time_of_flight

    def tof_to_wavelength(self, time_of_flight):
        return self.h_m_n * time_of_flight / self.flight_distance

    def wavelength_to_dspacing(self, wavelength):
        return wavelength / (2 * np.sin(self.theta))

    def tof_to_dspacing(self, time_of_flight):
        wavelength = self.tof_to_wavelength(time_of_flight)
        return self.wavelength_to_dspacing(wavelength)

    def dspacing_to_wavelength(self,dspacing):
        return dspacing*2*np.sin(self.theta)

    def dspacing_to_q(self,dspacing):
        return 2*np.pi/dspacing

    def tof_to_energy(self,time_of_flight):
        tof = time_of_flight/1000
        return 10*1.675/3.2*(self.flight_distance/tof)**2

    def velocity_to_wavelength(self, velocity):
        return self.h_m_n / velocity
