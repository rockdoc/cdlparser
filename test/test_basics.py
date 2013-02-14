"""
Unit tests for basic CDL constructs.
"""
import os
import tempfile
import unittest
import cdlparser
import numpy as np

#---------------------------------------------------------------------------------------------------
class TestBasics(unittest.TestCase) :
#---------------------------------------------------------------------------------------------------
   def setUp(self) :
      cdltext = r"""netcdf basics {
         dimensions:
            lev = 1 ;
            lat = 2 ;
            lon = 3 ;
            time = unlimited ;
         variables:
            int tas(lev, lat, lon) ;
               tas:standard_name = "air_temperature" ;
               tas:units = "K" ;
               tas:radius = 6371000.0 ;
            double height(lev) ;
               height:standard_name = "height" ;
         // global attributes
            :Conventions = "CF-1.5" ;
            :comment = "cdlparser rocks!" ;
         data:
            tas = 0, 1, 2, 3, 4, 5 ;
            height = 10.0 ;
      }"""
      parser = cdlparser.CDL3Parser()
      self.tmpfile = tempfile.mkstemp(suffix='.nc')[1]
      self.dataset = parser.parse_text(cdltext, ncfile=self.tmpfile)

   def tearDown(self) :
      if os.path.exists(self.tmpfile) : os.remove(self.tmpfile)

   def test_global_atts(self) :
      self.assertTrue(self.dataset.Conventions == "CF-1.5")
      self.assertTrue(self.dataset.comment == "cdlparser rocks!")

   def test_dimensions(self) :
      self.assertTrue(len(self.dataset.dimensions) == 4)
      lev = self.dataset.dimensions['lev']
      self.assertTrue(len(lev) == 1)
      lat = self.dataset.dimensions['lat']
      self.assertTrue(len(lat) == 2)
      lon = self.dataset.dimensions['lon']
      self.assertTrue(len(lon) == 3)
      time = self.dataset.dimensions['time']
      self.assertTrue(len(time) == 0)
      self.assertTrue(time.isunlimited())

   def test_variables(self) :
      self.assertTrue(len(self.dataset.variables) == 2)

      tas = self.dataset.variables['tas']
      self.assertTrue(tas.standard_name == "air_temperature")
      self.assertTrue(tas.units == "K")
      self.assertTrue(tas.radius == np.float64(6371000.0))
      data = tas[:]
      self.assertTrue(data.shape == (1,2,3))
      expected = np.arange(6, dtype=np.int32)
      expected.shape = (1,2,3)
      self.assertTrue(np.array_equal(data, expected))

      ht = self.dataset.variables['height']
      self.assertTrue(ht.standard_name == "height")
      data = ht[:]
      self.assertTrue(data.shape == (1,))
      expected = np.array([10.0], dtype=np.float64)
      expected.shape = (1,)
      self.assertTrue(np.array_equal(data, expected))

#---------------------------------------------------------------------------------------------------
if __name__ == '__main__':
#---------------------------------------------------------------------------------------------------
   unittest.main()
