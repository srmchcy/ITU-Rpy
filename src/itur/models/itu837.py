# -*- coding: utf-8 -*-
import numpy as np
from astropy import units as u

from models.itu1144 import bilinear_2D_interpolator
from iturutils import load_data, dataset_dir, prepare_input_array,\
                      prepare_output_array, memory

class __ITU837():
    """Characteristics of precipitation for propagation modelling

    Available versions include:
    * P.837-1 (08/94) (Superseded)
    * P.837-2 (10/99) (Superseded)
    * P.837-3 (02/01) (Superseded)
    * P.837-4 (04/03) (Superseded)
    * P.837-5 (08/07) (Superseded)
    * P.837-6 (02/12) (Current version)
    """
    # This is an abstract class that contains an instance to a version of the
    # ITU-R P.837 recommendation.
    def __init__(self, version = 6):
        if version == 6:
            self.instance = _ITU837_6()
        elif version == 5:
            self.instance = _ITU837_5()
        elif version == 4:
            self.instance = _ITU837_4()
        elif version == 3:
            self.instance = _ITU837_3()
        elif version == 2:
            self.instance = _ITU837_2()
        elif version == 1:
            self.instance = _ITU837_1()
        else:
            raise ValueError('Version ' + str(version) + ' is not implemented' +
            ' for the ITU-R P.837 model.')

    @property
    def __version__(self):
        return self.instance.__version__

    def rain_percentage_probability(self, lat, lon):
        # Abstract method to compute the rain height
        return self.instance.rain_percentage_probability(lat, lon)

    def rainfall_rate(self, lat, lon, p):
        # Abstract method to compute the zero isoterm height
        return self.instance.rainfall_rate(lat, lon, p)


class _ITU837_6():

    def __init__(self):
        self.__version__ = 6
        self.year = 2012
        self.month = 2
        self.link = 'https://www.itu.int/rec/R-REC-P.837-6-201202-I/en'

        self._Pr6 = {}
        self._Mt = {}
        self._Beta = {}


    def Pr6(self, lat, lon):
        if not self._Pr6:
            vals = load_data(dataset_dir + '837/ESARAIN_PR6_v5.txt')
            lats = load_data(dataset_dir + '837/ESARAIN_LAT_v5.txt')
            lons = load_data(dataset_dir + '837/ESARAIN_LON_v5.txt')
            self._Pr6 = bilinear_2D_interpolator(lats, lons, vals)

        return self._Pr6(np.array([lat.ravel(), lon.ravel()]).T).reshape(lat.shape)

    def Mt(self, lat, lon):
        if not self._Mt:
            vals = load_data(dataset_dir + '837/ESARAIN_MT_v5.txt')
            lats = load_data(dataset_dir + '837/ESARAIN_LAT_v5.txt')
            lons = load_data(dataset_dir + '837/ESARAIN_LON_v5.txt')
            self._Mt = bilinear_2D_interpolator(lats, lons, vals)

        return self._Mt(np.array([lat.ravel(), lon.ravel()]).T).reshape(lat.shape)

    def Beta(self, lat, lon):
        if not self._Beta:
            vals = load_data(dataset_dir + '837/ESARAIN_BETA_v5.txt')
            lats = load_data(dataset_dir + '837/ESARAIN_LAT_v5.txt')
            lons = load_data(dataset_dir + '837/ESARAIN_LON_v5.txt')
            self._Beta = bilinear_2D_interpolator(lats, lons, vals)

        return self._Beta(np.array([lat.ravel(), lon.ravel()]).T).reshape(lat.shape)


    def rain_percentage_probability(self, lat_d, lon_d):
        """

        """
        Pr6 = self.Pr6(lat_d, lon_d)
        Mt = self.Mt(lat_d, lon_d)
        Beta = self.Beta(lat_d, lon_d)

         # Step 3: Convert MT and β to Mc and Ms as follows:
        Ms = (1 - Beta) * Mt

        # Step 4: Derive the percentage propability of rain in an average year, P0:
        P0 = Pr6 * (1 - np.exp(-0.0079 * (Ms / Pr6) ) ) # Eq. 1

        return P0

    def rainfall_rate(self, lat_d, lon_d, p):
        """
        """
        Pr6 = self.Pr6(lat_d, lon_d)
        Mt = self.Mt(lat_d, lon_d)
        Beta = self.Beta(lat_d, lon_d)

        # Step 3: Convert MT and β to Mc and Ms as follows:
        Mc = Beta * Mt
        Ms = (1 - Beta) * Mt

        # Step 4: Derive the percentage propability of rain in an average year, P0:
        P0 = np.where(Pr6 > 0 , Pr6 * (1 - np.exp(-0.0079 * (Ms / Pr6) ) ), 0) # Eq. 1

        # Step 5: Derive the rainfall rate, Rp, exceeded for p% of the average year, where p <= P0, from:
        def computeRp(P0, Mc, Ms):
            a = 1.09                        # Eq. 2d
            b = (Mc + Ms) / (21797 * P0)    # Eq. 2e
            c = 26.02 * b                   # Eq. 2f

            A = a * b                       # Eq. 2a
            B = a + c * np.log( p / P0 )    # Eq. 2b
            C = np.log(p / P0)              # Eq. 2c

            Rp = (-B + np.sqrt(B**2 - 4 * A * C)) / (2 * A) # Eq. 2

            return Rp

        # The value of Rp can only be computed for those values where p > P0
        Rp = np.where(np.isnan(P0) | (p > P0), 0, computeRp(P0, Mc, Ms))
        return Rp


__model = __ITU837()

def change_version(new_version):
    """
    Change the version of the ITU-R P.837 recommendation currently being used.

    Parameters
    ----------
    new_version : int
        Number of the version to use.
        Valid values are:
        * P.837-1 (08/94) (Superseded)
        * P.837-2 (10/99) (Superseded)
        * P.837-3 (02/01) (Superseded)
        * P.837-4 (04/03) (Superseded)
        * P.837-5 (08/07) (Superseded)
        * P.837-6 (02/12) (Current version)
    """
    global __model
    __model = __ITU837(new_version)

def get_version():
    """
    Obtain the version of the ITU-R P.837 recommendation currently being used.
    """
    global __model
    return __model.__version__


@memory.cache
def rain_percentage_probability(lat, lon):
    """
    A method to compute the percentage probability of rain in an average year, P0

    Parameters
    ----------
    lat : number, sequence, or numpy.ndarray
        Latitudes of the receiver points
    lon : number, sequence, or numpy.ndarray
        Longitudes of the receiver points

    Returns
    -------
    P0: numpy.ndarray
        Percentage probability of rain in an average year

    References:
    -----------
    [1] Characteristics of precipitation for propagation modelling
    https://www.itu.int/rec/R-REC-P.837/en
    """
    global __model
    type_output = type(lat)
    lat = prepare_input_array(lat)
    lon = prepare_input_array(lon)
    lon = np.mod(lon, 360)
    val = __model.rain_percentage_probability(lat, lon)
    return prepare_output_array(val, type_output) * u.pct


@memory.cache
def rainfall_rate(lat, lon, p):
    """
    A method to compute the rainfall rate exceeded for p% of the average year

    Parameters
    ----------
    lat : number, sequence, or numpy.ndarray
        Latitudes of the receiver points
    lon : number, sequence, or numpy.ndarray
        Longitudes of the receiver points
    p : number
        Percentage of time exceeded for p% of the average year

    Returns
    -------
    R001: numpy.ndarray
        Rainfall rate exceeded for p% of the average year

    References:
    -----------
    [1] Characteristics of precipitation for propagation modelling
    https://www.itu.int/rec/R-REC-P.837/en
    """
    global __model
    type_output = type(lat)
    lat = prepare_input_array(lat)
    lon = prepare_input_array(lon)
    lon = np.mod(lon, 360)
    val = __model.rainfall_rate(lat, lon, p)
    return prepare_output_array(val, type_output) * u.mm / u.hr


def unavailability_from_rainfall_rate(lat, lon, R):
    """
    A method to estimate the percentage of time of the average year that a given
    rainfall rate (R) is exceeded. This method calls successively to the
    `rainfall_rate` method and interpolates its value.

    Parameters
    ----------
    lat : number, sequence, or numpy.ndarray
        Latitudes of the receiver points
    lon : number, sequence, or numpy.ndarray
        Longitudes of the receiver points
    R : number, sequence, or numpy.ndarray
        Rainfall rate (mm/h)

    Returns
    -------
    p: numpy.ndarray
        Rainfall rate exceeded for p% of the average year

    References:
    -----------
    [1] Characteristics of precipitation for propagation modelling
    https://www.itu.int/rec/R-REC-P.837/en
    """
    global __model
    lat = prepare_input_array(lat)
    lon = prepare_input_array(lon)
    lon = np.mod(lon, 360)
    #TODO: write this function