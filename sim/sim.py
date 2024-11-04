"""
==========================================================================
sim.py
==========================================================================
Dataflow graph simulation.

Author : Cheng Tan
  Date : Jun 13, 2024

"""

# from pymtl3                       import *
# from ...lib.messages              import *
# from ..CGRAFL                     import CGRAFL
# from ...lib.dfg_helper            import *
from dfg_helper            import *

import os

def test_fl():
  target_json = "dfg_fir.json"
  script_dir  = os.path.dirname(__file__)
  file_path   = os.path.join( script_dir, target_json )
  print("[cheng] Hello world!")
  # DataType = mk_data( 16, 1 )
  # CtrlType = mk_ctrl()

  const_data = [ 0, 1, 2, 3, 4, 5 ]

  # const_data = [ DataType( 0, 1  ),
  #                DataType( 1, 1  ),
  #                DataType( 2, 1  ),
  #                DataType( 3, 1  ),
  #                DataType( 4, 1  ),
  #                DataType( 5, 1 ) ]

  data_spm = [ 3 for _ in range(100) ]
  fu_dfg = DFG( file_path, const_data, data_spm )

  print("[cheng] Created DFG!")
  print( "----------------- FL test ------------------" )
  return
  # FL golden reference
  CGRAFL( fu_dfg, DataType, CtrlType, const_data )#, data_spm )
  print()

# Defining main function 
def main(): 
  test_fl()


# Using the special variable  
# __name__ 
if __name__=="__main__": 
    main() 

