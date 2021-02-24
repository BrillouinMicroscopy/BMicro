import numpy as np

from bmlab.image import fit_circle, find_max_in_radius


class Orientation(object):

    def __init__(self, rotation=0,
                 reflection={'vertically': False, 'horizontally': False}):
        self.rotation = rotation
        self.reflection = reflection

    def set_rotation(self, num_rots):
        self.rotation = num_rots

    def set_reflection(self, **kwargs):
        axes = ['vertically', 'horizontally']
        for a in axes:
            if a in kwargs:
                self.reflection[a] = kwargs[a]


class ExtractionModel(object):

    def __init__(self):
        self.points = {}
        self.circle_fits = {}
        self.extracted_values = {}

    def add_point(self, calib_key, xdata, ydata):
        if calib_key not in self.points:
            self.points[calib_key] = []
        self.points[calib_key].append((xdata, ydata))
        if len(self.points[calib_key]) >= 3:
            self.circle_fits[calib_key] = fit_circle(self.points[calib_key])

    def get_points(self, calib_key):
        if calib_key in self.points:
            return self.points[calib_key]
        return []

    def optimize_points(self, calib_key, img):
        points = self.get_points(calib_key)
        self.clear_points(calib_key)

        for p in points:
            new_point = find_max_in_radius(img, p, 10)
            # Warning: x-axis in imshow is 1-axis in img, y-axis is 0-axis
            self.add_point(
                calib_key, new_point[0], new_point[1])

    def clear_points(self, calib_key):
        self.points[calib_key] = []
        self.circle_fits[calib_key] = None

    def get_circle_fit(self, calib_key):
        return self.circle_fits.get(calib_key)

    def set_extracted_values(self, calib_key, phis, values):
        self.extracted_values[calib_key] = [(phi, value)
                                            for phi, value in
                                            zip(phis, values)]

    def get_extracted_values(self, calib_key):
        values = self.extracted_values.get(calib_key)
        if values:
            return np.array(values)
        return []


class CalibrationModel(object):

    def __init__(self):
        self.brillouin_regions = {}

    def add_brillouin_region(self, calib_key, region):

        if calib_key not in self.brillouin_regions:
            self.brillouin_regions[calib_key] = []

        self.brillouin_regions[calib_key].append(region)


class Setup(object):

    def __init__(self, key, name, pixel_size, lambda0, focal_length,
                 vipa, calibration):
        """

        Parameters
        ----------
        key: str
            ID for the setup
        name: str
            Name of setup
        pixel_size: float
            pixel size of the camera [m]
        lambda0: float
            laser wavelength [m]
        focal_length: float
            focal length of the lens behind the VIPA [m]
        vipa
        calibration
        """
        self.key = key
        self.name = name
        self.pixel_size = pixel_size
        self.lambda0 = lambda0
        self.focal_length = focal_length
        self.vipa = vipa
        self.calibration = calibration


class VIPA(object):

    def __init__(self, d, n, theta, order):
        """ Start values for VIPA fit

        Parameters
        ----------
        d : float
            width of the cavity [m]
        n : float
            refractive index of the cavity [-]
        theta : float
            angle [rad]
        order: int
            observed order of the VIPA spectrum
        """
        self.d = d
        self.n = n
        self.theta = theta
        self.order = order


class Calibration(object):

    def __init__(self, num_brillouin_samples, shift_methanol=None,
                 shift_water=None):
        """

        Parameters
        ----------
        num_brillouin_samples: int
            Number of samples
        shift_methanol: float
            ??
        shift_water: float
            ??
        """

        self.num_brillouin_samples = num_brillouin_samples
        self.shift_methanol = shift_methanol
        self.shift_water = shift_water


AVAILABLE_SETUPS = [
    Setup(key='S0',
          name='780 nm @ Biotec R340',
          pixel_size=6.5e-6,
          lambda0=780.24e-9,
          focal_length=0.2,
          vipa=VIPA(d=0.006743,
                    n=1.45367,
                    theta=0.8 * 2 * np.pi / 360,
                    order=0),
          calibration=Calibration(num_brillouin_samples=2,
                                  shift_methanol=3.78e9,
                                  shift_water=5.066e9)),
    Setup(key='S1',
          name='780 nm @ Biotec R340 old',
          pixel_size=6.5e-6,
          lambda0=780.24e-9,
          focal_length=0.2,
          vipa=VIPA(d=0.006743,
                    n=1.45367,
                    theta=0.8 * 2 * np.pi / 360,
                    order=0),
          calibration=Calibration(num_brillouin_samples=1,
                                  shift_methanol=3.78e9)),
    Setup(key='S2',
          name='532 nm @ Biotec R314',
          pixel_size=6.5e-6,
          lambda0=532e-9,
          focal_length=0.2,
          vipa=VIPA(d=0.003371,
                    n=1.46071,
                    theta=0.8 * 2 * np.pi / 360,
                    order=0),
          calibration=Calibration(num_brillouin_samples=2,
                                  shift_methanol=5.54e9,
                                  shift_water=7.43e9))
]
