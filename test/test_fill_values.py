"""
Unit tests for correct handling of fill values.
"""
import os
import tempfile
import unittest
import cdlparser
import numpy as np

#---------------------------------------------------------------------------------------------------
class TestFillValues(unittest.TestCase) :
#---------------------------------------------------------------------------------------------------
   def setUp(self) :
      cdltext = r"""netcdf fillvalues {
         dimensions:
            lat = 2 ;
            lon = 2 ;
            time = unlimited ;
         variables:
            int time(time) ;
               time:units = "days since 1970-01-01" ;
            float lat(lat) ;
               lat:standard_name = "latitude" ;
            float lon(lon) ;
               lon:standard_name = "longitude" ;
            float tas(time, lat, lon) ;
               tas:standard_name = "air_temperature" ;
               tas:_FillValue = -1.0e30f ;
         // global attributes
            :comment = "fill value tests" ;
         data:
            time = 0, 30, 60 ;
            lat = 0.0f, 10.0f ;
            lon = 0.0f, 20.0f ;
            // final 2 values are missing from tas data array and thus
            // should be automatically assigned as fill values
            tas = _, _, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f ;
      }"""
      parser = cdlparser.CDL3Parser()
      self.tmpfile = tempfile.mkstemp(suffix='.nc')[1]
      self.dataset = parser.parse_text(cdltext, ncfile=self.tmpfile)

   def tearDown(self) :
      if os.path.exists(self.tmpfile) : os.remove(self.tmpfile)

   def test_dimensions(self) :
      self.assertTrue(len(self.dataset.dimensions) == 3)
      time = self.dataset.dimensions['time']
      self.assertTrue(len(time) == 3)
      self.assertTrue(time.isunlimited())

   def test_variables(self) :
      self.assertTrue(len(self.dataset.variables) == 4)
      var = self.dataset.variables['tas']
      self.assertTrue(var.standard_name == "air_temperature")
      self.assertTrue(var._FillValue == np.float32(-1e30))
      data = var[:]
      self.assertTrue(np.ma.isMA(data))
      self.assertTrue(data.fill_value == np.float32(-1e30))
      self.assertTrue(data.shape == (3,2,2))
      data = data.flatten()
      self.assertTrue(data[0] is np.ma.masked)
      self.assertTrue(data[-1] is np.ma.masked)
      self.assertTrue(data.data[0] == np.float32(-1e30))
      self.assertTrue(data.data[-1] == np.float32(-1e30))
      self.assertTrue(data[2] == np.float32(3.0))
      self.assertTrue(data[9] == np.float32(10.0))

#---------------------------------------------------------------------------------------------------
if __name__ == '__main__':
#---------------------------------------------------------------------------------------------------
   unittest.main()
