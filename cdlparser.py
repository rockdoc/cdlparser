# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

"""
A python parser for reading files encoded in netCDF-3 CDL format. The parser is based upon the
flex and yacc files used by the ncgen3 utility that ships with the standard netCDF distribution.

The basic usage idiom is as follows:

myparser = CDL3Parser(...)
myparser.parse(cdlfilename, ...)

If the input CDL file is valid then the above code should result in a netCDF-3 file being
generated, either in the same directory as the CDL file (and with the .cdl extension replaced
with .nc), or else in the location specified via the ncfile keyword argument to the parse()
method.

Package Dependencies:
   PLY - http://www.dabeaz.com/ply/
   netcdf4-python - http://code.google.com/p/netcdf4-python/

Creator: Phil Bentley
"""
__version_info__ = (0, 0, 1, 'beta', 0)
__version__ = "%d.%d.%d-%s" % __version_info__[0:4]

import sys, os, logging
import ply.lex as lex
from ply.lex import TOKEN
import ply.yacc as yacc
import netCDF4 as nc4

# default fill values for netCDF-3 data types (as defined in netcdf.h include file)
NC_FILL_BYTE   = -127
NC_FILL_CHAR   = chr(0)
NC_FILL_SHORT  = -32767
NC_FILL_INT    = -2147483647
NC_FILL_FLOAT  = 9.9692099683868690e+36   # will get rounded to 9.96921e+36
NC_FILL_DOUBLE = 9.9692099683868690e+36

# miscellaneous constants as defined in ncgen3.l file
FILL_STRING = "_"
XDR_INT_MIN = -2147483648
XDR_INT_MAX =  2147483647

# netcdf to numpy data type map
NC_NP_DATA_TYPE_MAP = {
   'byte':    'b',
   'char':    'c',
   'short':   's',
   'int':     'i',
   'integer': 'i',
   'long':    'i',
   'float':   'f',
   'real':    'f',
   'double':  'd'
}

# default logging options
DEFAULT_LOG_LEVEL  = logging.INFO
DEFAULT_LOG_FORMAT = "[%(levelname)s] %(name)s: %(message)s"

# Exception class for CDL syntax errors
class CDLSyntaxError(Exception) :
   pass

# Exception class for CDL content errors
class CDLContentError(Exception) :
   pass

#---------------------------------------------------------------------------------------------------
class CDLParser(object) :
#---------------------------------------------------------------------------------------------------
   """ Base class for a CDL lexer/parser that has tokens and rules defined as methods."""
   tokens = []
   precedence = []

   def __init__(self, **kw) :
      self.debug = kw.get('debug', 0)
      self.log_level = kw.get('log_level', DEFAULT_LOG_LEVEL)
      self.names = { }
      try:
         modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
      except:
         modname = "parser" + "_" + self.__class__.__name__
      self.debugfile = modname + ".dbg"
      self.tabmodule = modname + "_" + "parsetab"
      self.init_logger()

      # Build the lexer and parser
      self.lexer = lex.lex(module=self, debug=self.debug)
      self.parser = yacc.yacc(module=self, debug=self.debug, debugfile=self.debugfile,
         tabmodule=self.tabmodule)

   def parse(self, cdlfile, ncfile=None) :
      self.ncfile = ncfile or os.path.splitext(cdlfile)[0] + '.nc'
      f = open(cdlfile)
      data = f.read()   # FIXME: can we parse input w/o reading entire CDL file into memory?
      f.close()
      self.parser.parse(input=data, lexer=self.lexer)

   def init_logger(self) :
      """Configure the global logger object."""
      console = logging.StreamHandler(stream=sys.stderr)
      console.setLevel(self.log_level)
      fmtr = logging.Formatter(DEFAULT_LOG_FORMAT)
      console.setFormatter(fmtr)
      self.logger = logging.getLogger('cdlparser')
      self.logger.addHandler(console)
      self.logger.setLevel(self.log_level)

#---------------------------------------------------------------------------------------------------
class CDL3Parser(CDLParser) :
#---------------------------------------------------------------------------------------------------
   """Class for parsing a CDL file encoded in netCDF-3 classic format."""
   start = "ncdesc"

   # netCDF-3 reserved words - mainly data types
   reserved_words = {
      'byte':    'BYTE_K',
      'char':    'CHAR_K',
      'short':   'SHORT_K',
      'int':     'INT_K',
      'integer': 'INT_K',
      'long':    'INT_K',
      'float':   'FLOAT_K',
      'real':    'FLOAT_K',
      'double':  'DOUBLE_K',
   'unlimited':  'NC_UNLIMITED_K'
   }

   # the full list of CDL tokens to parse
   tokens = [
      'NETCDF', 'DIMENSIONS', 'VARIABLES', 'DATA', 'IDENT', 'TERMSTRING',
      'BYTE_CONST', 'CHAR_CONST', 'SHORT_CONST', 'INT_CONST', 'FLOAT_CONST', 'DOUBLE_CONST',
      'FILLVALUE', 'COMMENT', 'EQUALS', 'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'EOL'
   ] + list(set(reserved_words.values()))

   # literal characters
   literals = [',',':']

   # Partially relaxed version of the UTF8 character set, and the one used in the ncgen3.l flex file.
   UTF8 = r'([\xC0-\xD6][\x80-\xBF])|([\xE0-\xEF][\x80-\xBF][\x80-\xBF])|([\xF0-\xF7][\x80-\xBF][\x80-\xBF][\x80-\xBF])'

   # Don't permit control characters or '/' in names, but other special
   # chars OK if escaped.  Note that to preserve backwards
   # compatibility, none of the characters _.@+- should be escaped, as
   # they were previously permitted in names without escaping.
   idescaped = r"""\\[ !"#$%&'()*,:;<=>?\[\\\]^`{|}~]"""
   ID = r'([a-zA-Z_]|' + UTF8 + r'|\\[0-9])([a-zA-Z0-9_.@+-]|' + UTF8 + r'|'  + idescaped + r')*'

   escaped = r'\\.'
   nonquotes = r'([^"\\]|' + escaped + r')*'
   termstring = r'\"' + nonquotes + r'\"'

   exp = r'([eE][+-]?[0-9]+)'
   float_const  = r'[+-]?[0-9]*\.[0-9]*' + exp + r'?[Ff]|[+-]?[0-9]*' + exp + r'[Ff]'
   double_const = r'[+-]?[0-9]*\.[0-9]*' + exp + r'?[LlDd]?|[+-]?[0-9]*' + exp + r'[LlDd]?'
   byte_const = r"([+-]?[0-9]+[Bb])|" + \
                r"(\'[^\\]\')|(\'\\.\')|" + \
                r"(\'\\[0-7][0-7]?[0-7]?\')|" + \
                r"(\'\\[xX][0-9a-fA-F][0-9a-fA-F]?\')"

   def __init__(self, **kw) :
      CDLParser.__init__(self, **kw)
      self.dryrun = False
      self.file_format = kw.get("file_format", "NETCDF3_CLASSIC")
      self.ncdataset = None
      self.curr_dim = None
      self.curr_var = None
      self.ndims = 0
      self.rec_dim = -1

   ### TOKEN DEFINITIONS

   # definitions of simple tokens
   t_EQUALS = r'='
   t_LBRACE = r'\{'
   t_RBRACE = r'\}'
   t_LPAREN = r'\('
   t_RPAREN = r'\)'
   t_EOL    = r';'

   # ignored characters - whitespace, basically
   t_ignore  = ' \r\t\f'

   # opening stanza - pull out the netcdf filename
   def t_NETCDF(self, t) :
      r'(netcdf|NETCDF|netCDF)[ \t]+[^\{]+'
      parts = t.value.split()
      if len(parts) < 2 :
         raise CDLSyntaxError("A netCDF name is required")
      netcdfname = parts[1]
      # TODO: deescapify(netcdfname);  # so "\5foo" becomes "5foo", for example
      t.value = netcdfname
      return t

   # main section identifiers
   def t_SECTION(self, t) :
      r'dimensions:|DIMENSIONS:|variables:|VARIABLES:|data:|DATA:'
      t.type = t.value[:-1].upper()
      return t

   # character strings
   @TOKEN(termstring)
   def t_TERMSTRING(self, t) :
      # TODO: expand_escapes(termstring,(char *)yytext,yyleng) - defined in ncgen3/escapes.c
      t.value = t.value[1:-1]   # eval(t.value) might be preferable here
      return t

   # comments
   def t_COMMENT(self, t) :
      r'\/\/.*'
      pass

   # identifier - attribute, dimension or variable name
   @TOKEN(ID)
   def t_IDENT(self, t) :
      if t.value == FILL_STRING :
         t.type = "FILLVALUE"
      elif t.value.lower() in self.reserved_words :
         t.value = t.value.lower()
         t.type = self.reserved_words[t.value]
      else :
         t.type = "IDENT"
      return(t)

   # numeric constants (order of appearance is extremely important and differs from ncgen3.l file)
   @TOKEN(float_const)
   def t_FLOAT_CONST(self, t) :
      #r'[+-]?[0-9]*\.[0-9]*' + exp + r'?[Ff]|[+-]?[0-9]*' + exp + r'[Ff]'
      try :
         float_val = float(t.value[:-1])
      except :
         errmsg = "Bad float constant: %s" % t.value
         raise CDLContentError(errmsg)
      t.value = float_val
      return t

   @TOKEN(double_const)
   def t_DOUBLE_CONST(self, t) :
      #r'[+-]?[0-9]*\.[0-9]*' + exp + r'?[LlDd]?|[+-]?[0-9]*' + exp + r'[LlDd]?'
      try :
         if t.value[-1] in "dD" :
            double_val = float(t.value[:-1])
         else :
            double_val = float(t.value)
      except :
         errmsg = "Bad double constant: %s" % t.value
         raise CDLContentError(errmsg)
      t.value = double_val
      return t

   def t_SHORT_CONST(self, t) :
      r'[+-]?([0-9]+|0[xX][0-9a-fA-F]+)[sS]'
      #r'[+-]?[0-9]+[sS]|0[xX][0-9a-fA-F]+[sS]'   # original regex in ncgen3.l file
      try :
         int_val = int(eval(t.value[:-1]))
      except :
         errmsg = "Bad short constant: %s" % t.value
         raise CDLContentError(errmsg)
      if int_val < -32768 or int_val > 32767 :
         errmsg = "Short constant is outside valid range (-32768 -> 32767): %s" % int_val
         raise CDLContentError(errmsg)
      t.value = int_val
      return t

   @TOKEN(byte_const)
   def t_BYTE_CONST(self, t) :
      #r'[+-]?[0-9]+[Bb]'        # modified regex
      #r'[+-]?[0-9]*[0-9][Bb]'   # original regex in ncgen3.l file
      try :
         if t.value[0] == "'" :
            int_val = ord(eval(t.value))
         else :
            int_val = int(t.value[:-1])
      except :
         errmsg = "Bad byte constant: %s" % t.value
         raise CDLContentError(errmsg)
      if int_val < -128 or int_val > 127 :
         errmsg = "Byte constant outside valid range (-128 -> 127): %s" % int_val
         raise CDLContentError(errmsg)
      t.value = int_val
      return t

   # TODO: the next two tokens are as per ncgen.l, but could usefully be combined into one method

   # octal or hex integer
   def t_LONG_CONST(self, t) :
      r'0[xX]?[0-9a-fA-F]+[lL]?'
      try :
         long_val = long(eval(t.value))
      except :
         errmsg = "Bad long constant: %s" %  t.value
         raise CDLContentError(errmsg)
      if long_val < XDR_INT_MIN or long_val > XDR_INT_MAX :
         t.value = float(long_val)
         t.type = "DOUBLE_CONST"   # FIXME: this is what ncgen does, but why?
      else :
         t.value = int(long_val)
         t.type = "INT_CONST"
      return t

   # regular decimal integer
   def t_NUMERIC_CONST(self, t) :
      r'[+-]?([1-9][0-9]*|0)[lL]?'
      try :
         long_val = long(eval(t.value))
      except :
         errmsg = "Bad numeric constant: %s" %  t.value
         raise CDLContentError(errmsg)
      if long_val < XDR_INT_MIN or long_val > XDR_INT_MAX :
         t.value = float(long_val)
         t.type = "DOUBLE_CONST"   # FIXME: this is what ncgen does, but why?
      else :
         t.value = int(long_val)
         t.type = "INT_CONST"
      return t

   # newlines
   def t_newline(self, t):
      r'\n+'
      t.lexer.lineno += len(t.value)

   # error handler
   # TODO: add some useful behaviour
   def t_error(self, t):
      print("Illegal character '%s'" % t.value[0])
      t.lexer.skip(1)

   def lextest(self, data) :
      self.lexer.input(data)
      print "-----"
      while 1 :
         t = self.lexer.token()
         if not t : break
         print "type: %-15s\tvalue: %s" % (t.type, t.value)
      print "-----"

   ### PARSING RULES

   def p_ncdesc(self, p) :
      """ncdesc : NETCDF init_netcdf LBRACE dimsection vasection datasection RBRACE"""
      if self.ncdataset : self.ncdataset.close()
      self.logger.info("Closed netCDF file")

   def p_init_netcdf(self, p) :
      """init_netcdf :"""
      self.ncdataset = nc4.Dataset(self.ncfile, 'w', format=self.file_format)
      self.logger.info("Initialised netCDF file " + self.ncfile)

   def p_dimsection(self, p) :
      """dimsection : DIMENSIONS dimdecls
                    | empty"""

   def p_dimdecls(self, p) :
      """dimdecls : dimdecls dimdecline EOL
                  | dimdecline EOL"""

   def p_dimdecline(self, p) :
      """dimdecline : dimdecline ',' dimdecl
                    | dimdecl"""

   def p_dimdecl(self, p) :
      """dimdecl : dimd EQUALS INT_CONST
                 | dimd EQUALS DOUBLE_CONST
                 | dimd EQUALS NC_UNLIMITED_K"""
      dimname = ""
      if isinstance(p[3], basestring) :
         if p[3] == "unlimited" :
            if self.rec_dim != -1 : raise CDLContentError("Only one UNLIMITED dimension is allowed.")
            self.rec_dim = self.ndims
            dimname = p[1]
            dimlen = 0
            self.ndims += 1
      else :
         dimname = p[1]
         dimlen = int(p[3])
         self.ndims += 1
      if dimname :
         if dimlen <= 0 : CDLContentError("Length of dimension '%s' must be positive." % dimname)
         self.ncdataset.createDimension(dimname, dimlen)
         self.logger.info("Created dimension %s with length %s" % (dimname, dimlen))

   def p_dimd(self, p) :
      """dimd : dim"""
      if p[1] in self.ncdataset.dimensions :
         raise CDLContentError("Duplicate declaration for dimension '%s'." % p[1])
      p[0] = p[1]

   def p_dim(self, p) :
      """dim : IDENT"""
      p[0] = p[1]

   def p_vasection(self, p) :
      """vasection : VARIABLES vadecls
                   | gattdecls
                   | empty"""

   def p_vadecls(self, p) :
      """vadecls : vadecls vadecl EOL
                 | vadecl EOL"""

   def p_vadecl(self, p) :
      """vadecl : vardecl
                | attdecl
                | gattdecl"""

   def p_vardecl(self, p) :
      """vardecl : type varlist"""

   def p_varlist(self, p) :
      """varlist : varlist ',' varspec
                 | varspec"""
      if len(p) == 2 :
         p[0] = p[1:]
      else :
         p[0] = p[1] + p[3:]

   def p_varspec(self, p) :
      """varspec : var dimspec"""
      if p[1] in self.ncdataset.variables :
         raise CDLContentError("Duplicate declaration of variable %s" % p[1])
      self.curr_var = self.ncdataset.createVariable(p[1], self.datatype, p[2], shuffle=False)
      self.logger.info("Created variable %s with data type %s and dimensions %s" % (p[1], self.datatype, p[2]))

   def p_var(self, p) :
      """var : IDENT"""
      p[0] = p[1]

   def p_dimspec(self, p) :
      """dimspec : LPAREN dimlist RPAREN
                 | empty"""
      if len(p) > 2 : p[0] = p[2]

   def p_dimlist(self, p) :
      """dimlist : dimlist ',' vdim
                 | vdim"""
      #print "dimlist: ", p[:]
      if len(p) == 2 :
         p[0] = p[1:]
      else :
         p[0] = p[1] + p[3:]

   def p_vdim(self, p) :
      """vdim : dim"""
      p[0] = p[1]

   def p_gattdecls(self, p) :
      """gattdecls : gattdecls gattdecl EOL
                   | gattdecl EOL"""

   def p_gattdecl(self, p) :
      """gattdecl : gatt EQUALS attvallist"""
      if self.ncdataset :
         self.ncdataset.setncattr(p[1], p[3])
         self.logger.info("Created global attribute %s=%s" % (p[1], p[3]))

   def p_attdecl(self, p) :
      """attdecl : att EQUALS attvallist"""
      # TODO: check for _FillValue attribute
      if self.curr_var :
         self.curr_var.setncattr(p[1], p[3])
         self.logger.info("Created var attribute %s=%s" % (p[1], p[3]))

   def p_att(self, p) :
      """att : avar ':' attr"""
      p[0] = p[3]

   def p_gatt(self, p) :
      """gatt : ':' attr"""
      p[0] = p[2]

   def p_avar(self, p) :
      """avar : var"""
      if self.ncdataset : self.curr_var = self.ncdataset.variables[p[1]]
      p[0] = p[1]

   def p_attr(self, p) :
      """attr : IDENT"""
      p[0] = p[1]

   def p_attvallist(self, p) :
      """attvallist : attvallist ',' aconst
                    | aconst"""
      #print "attlist:", p[:]
      if len(p) == 2 :
         p[0] = p[1:]
      else :
         p[0] = p[1] + p[3:]

   def p_aconst(self, p) :
      """aconst : attconst"""
      p[0] = p[1]

   def p_attconst(self, p) :
      """attconst : BYTE_CONST
                  | CHAR_CONST
                  | SHORT_CONST
                  | INT_CONST
                  | FLOAT_CONST
                  | DOUBLE_CONST
                  | TERMSTRING"""
      p[0] = p[1]

   def p_datasection(self, p) :
      """datasection : DATA datadecls
                     | DATA
                     | empty"""

   def p_datadecls(self, p) :
      """datadecls : datadecls datadecl EOL
                   | datadecl EOL"""

   def p_datadecl(self, p) :
      """datadecl : avar EQUALS constlist"""
      # TODO: pad out with fill values if array length is less than variable size
      if self.ncdataset :
         var = self.ncdataset.variables[p[1]]
         var[:] = p[3]
         self.logger.info("Set data values for variable %s" % (p[1]))

   def p_constlist(self, p) :
      """constlist : constlist ',' dconst
                   | dconst"""
      # FIXME: repeatedly appending values to a list will be inefficient for large data arrays
      if len(p) == 2 :
         p[0] = p[1:]
      else :
         p[0] = p[1] + p[3:]

   def p_dconst(self, p) :
      """dconst : const"""
      p[0] = p[1]

   def p_const(self, p) :
      """const : BYTE_CONST
               | CHAR_CONST
               | SHORT_CONST
               | INT_CONST
               | FLOAT_CONST
               | DOUBLE_CONST
               | TERMSTRING
               | FILLVALUE"""
      # return the value of the constant, or the current variable's fill value if the specified
      # constant value is the string '_'.
      if p[1] == FILL_STRING :
         if self.curr_var and self.curr_var.dtype.kind != 'S' :   # numeric variables only
            if '_FillValue' in self.curr_var.ncattrs() :
               p[0] = self.curr_var._FillValue
            else :
               p[0] = get_default_fill_value(self.curr_var.dtype.kind)
         else :
            p[0] = p[1]
      else :
         p[0] = p[1]

   def p_type(self, p) :
      """type : BYTE_K
              | CHAR_K
              | SHORT_K
              | INT_K
              | FLOAT_K
              | DOUBLE_K"""
      # return numpy data type corresponding to netcdf type keyword
      self.datatype = NC_NP_DATA_TYPE_MAP[p[1]]
      p[0] = self.datatype

   def p_empty(self, p) :
      'empty :'
      pass

   def p_error(self, p) :
      # TODO: needs refining
      if p :
         self.logger.error("Syntax error at token %s, value %s" % (p.type, p.value))
      yacc.token()

#---------------------------------------------------------------------------------------------------
def get_default_fill_value(datatype) :
#---------------------------------------------------------------------------------------------------
   """Returns the default netCDF fill value for the specified numpy data type code."""
   if datatype == 'b' :
      return NC_FILL_BYTE
   elif datatype == 'c' :
      return NC_FILL_CHAR
   elif datatype == 's' :
      return NC_FILL_SHORT
   elif datatype == 'i' :
      return NC_FILL_INT
   elif datatype == 'f' :
      return NC_FILL_FLOAT
   elif datatype == 'd' :
      return NC_FILL_DOUBLE
   else :
      raise CDLContentError("Unrecognised data type '%s'" % datatype)

#---------------------------------------------------------------------------------------------------
def main() :
#---------------------------------------------------------------------------------------------------
   # rudimentary main function - primarily for testing purposes at this point in time
   debug = 0
   if len(sys.argv) < 2 :
      print "usage: python cldparser.py cdlfile [keyword=value, ...]"
      sys.exit(1)
   cdlfile = sys.argv[1]
   kwargs = {}
   if len(sys.argv) > 2 :
      keys = [x.split('=')[0] for x in sys.argv[2:]]
      vals = [eval(x.split('=')[1]) for x in sys.argv[2:]]
      kwargs = dict(zip(keys,vals))
   cdlparser = CDL3Parser(**kwargs)
   cdlparser.parse(cdlfile)

#---------------------------------------------------------------------------------------------------
if __name__ == '__main__':
#---------------------------------------------------------------------------------------------------
   main()
