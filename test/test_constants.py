"""
Unit tests for each of the recognised CDL constant types.
"""
import os
import tempfile
import unittest
import cdlparser
import numpy as np

#---------------------------------------------------------------------------------------------------
class TestConstants(unittest.TestCase) :
#---------------------------------------------------------------------------------------------------
   def setUp(self) :
      cdltext = r"""netcdf constants {
         dimensions:
            dim1 = 3 ;
         variables:
            float var1(dim1) ;
               var1:att1 = "dummy attribute" ;
         // global attributes
            :c1 = "foo" ;      // with spaces
            :c2="bar" ;        // w/o spaces
         
            :byte1 = 123b ;
            :byte2 = 'a' ;     // 97
            :byte3 = '\n' ;    // 10
         
            :short1 = 1234s ;
            :short2 = -888s ;
            :short3 = 0xFFs ;  // 255
            :short4 = 077s ;   // 63
         
            :int1 = -56789 ;
            :int2 = 123456 ;
            :int3 = 0666 ;     // 438
            :int4 = 0x2F ;     // 47
            :iarray = 1, 2, 3, 4 ;
         
            :float1 = 123.0f ;
            :float2 = 0.2718e1f ;
            :farray = 1.0f, 2.0f, 3.0f ;
         
            :double1 = 3.14159d ;
            :double2 = 0.010203 ;
            :darray = 1.0, 2.0, 3.0 ;
         data:
            var1 = 1.0f, 2.0f, _ ;
      }"""
      parser = cdlparser.CDL3Parser()
      self.tmpfile = tempfile.mkstemp(suffix='.nc')[1]
      self.dataset = parser.parse_text(cdltext, ncfile=self.tmpfile)

   def tearDown(self) :
      if os.path.exists(self.tmpfile) : os.remove(self.tmpfile)

   def test_string_constants(self) :
      self.assertTrue(self.dataset.c1 == "foo")
      self.assertTrue(self.dataset.c2 == "bar")

   def test_byte_constants(self) :
      self.assertTrue(self.dataset.byte1 == 123)
      self.assertTrue(type(self.dataset.byte1) == np.int8)
      self.assertTrue(self.dataset.byte2 == 97)
      self.assertTrue(type(self.dataset.byte2) == np.int8)
      self.assertTrue(self.dataset.byte3 == 10)
      self.assertTrue(type(self.dataset.byte3) == np.int8)

   def test_short_constants(self) :
      self.assertTrue(self.dataset.short1 == 1234)
      self.assertTrue(type(self.dataset.short1) == np.int16)
      self.assertTrue(self.dataset.short2 == -888)
      self.assertTrue(type(self.dataset.short2) == np.int16)
      self.assertTrue(self.dataset.short3 == 255)
      self.assertTrue(type(self.dataset.short3) == np.int16)
      self.assertTrue(self.dataset.short4 == 63)
      self.assertTrue(type(self.dataset.short4) == np.int16)

   def test_int_constants(self) :
      self.assertTrue(self.dataset.int1 == -56789)
      self.assertTrue(type(self.dataset.int1) == np.int32)
      self.assertTrue(self.dataset.int2 == 123456)
      self.assertTrue(type(self.dataset.int2) == np.int32)
      self.assertTrue(self.dataset.int3 == 438)
      self.assertTrue(type(self.dataset.int3) == np.int32)
      self.assertTrue(self.dataset.int4 == 47)
      self.assertTrue(type(self.dataset.int4) == np.int32)

   def test_float_constants(self) :
      self.assertTrue(self.dataset.float1 == np.float32(123.0))
      self.assertTrue(type(self.dataset.float1) == np.float32)
      self.assertTrue(self.dataset.float2 == np.float32(0.2718e1))
      self.assertTrue(type(self.dataset.float2) == np.float32)

   def test_double_constants(self) :
      self.assertTrue(self.dataset.double1 == np.float64(3.14159))
      self.assertTrue(type(self.dataset.double1) == np.float64)
      self.assertTrue(self.dataset.double2 == np.float64(0.010203))
      self.assertTrue(type(self.dataset.double2) == np.float64)

   def test_int_array(self) :
      expected = np.array([1,2,3,4], dtype=np.int32)
      self.assertTrue(np.array_equal(self.dataset.iarray, expected))

   def test_float_array(self) :
      expected = np.array([1,2,3], dtype=np.float32)
      self.assertTrue(np.array_equal(self.dataset.farray, expected))

   def test_double_array(self) :
      expected = np.array([1,2,3], dtype=np.float64)
      self.assertTrue(np.array_equal(self.dataset.darray, expected))

   def test_dimensions(self) :
      self.assertTrue(len(self.dataset.dimensions) == 1)
      self.assertTrue(self.dataset.dimensions.keys()[0] == "dim1")
      dim = self.dataset.dimensions['dim1']
      self.assertTrue(len(dim) == 3)

   def test_variables(self) :
      self.assertTrue(len(self.dataset.variables) == 1)
      self.assertTrue(self.dataset.variables.keys()[0] == "var1")
      var = self.dataset.variables['var1']
      self.assertTrue(var.att1 == "dummy attribute")
      data = var[:]
      self.assertTrue(np.ma.isMA(data))
      self.assertTrue(len(data) == 3)
      self.assertTrue(data[0] == np.float32(1.0))
      self.assertTrue(data[1] == np.float32(2.0))
      self.assertTrue(data[2] is np.ma.masked)

#---------------------------------------------------------------------------------------------------
if __name__ == '__main__':
#---------------------------------------------------------------------------------------------------
   unittest.main()
