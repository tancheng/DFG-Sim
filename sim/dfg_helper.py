"""
==========================================================================
dfg_helper.py
==========================================================================
Helper classes and functions to construct specific accelerator in FL and
RTL.

Author : Cheng Tan
  Date : Nov 3, 2024

"""

# from .messages   import *
from map_helper import *

import json

class Data:

  def __init__ (s, value, predicate):
    s.value = value
    s.predicate = predicate


class Node:

  def __init__(s, node_id, fu_type, operation_type, opt_predicate, const_index, input_node_ids,
                input_predicate_node, output_node_ids):
    s.node_id = node_id
    s.fu_type = fu_type
    s.operation_type = operation_type
    s.opt_predicate = opt_predicate
    s.layer = 0
    s.const_index = const_index
    s.num_const = len(const_index)
    s.num_inputs = len(input_node_ids)
    # DataType               = mk_data( 16, 1 )
    s.input_node_ids = input_node_ids
    s.input_nodes = []
    s.output_nodes = []
    print("[cheng] s.input_node_ids: ", input_node_ids)
    s.input_predicate_node = input_predicate_node
    # s.input_value          = [ DataType( 0, 0 ) ] * s.num_input
    s.input_value = [Data(0, 0)] * s.num_inputs
    s.input_predicate = 1

    # 2D array for output since there will be multiple results generated,
    # and each of them will route to different successors.
    s.output_node_ids = output_node_ids
    s.num_outputs = [len(array) for array in output_node_ids]
    # s.output_value = [ [ DataType( 0, 0 ) for _ in array ]
    #                      for array in output_node ]
    s.output_value = [[Data(0, 0) for _ in array]
                       for array in output_node_ids]


    # We manually or automatically pick one BRH node to insert a live_out_ctrl
    # output, which will indicate the 'exit' point.
    s.live_out_ctrl = 0
    # Correspondingly, the live out value is indicated by the node with
    # live_out_val attribute.
    s.live_out_val = 0

    # This is used to update the input value without consideration of the
    # ordering, which means the we cannot support 'partial' operation, such
    # as 'LE'.
    s.current_input_index = 0
    s.current_output_index = 0

  # ---------------------------------------------------------------------
  # Update output value which will affect the input value of its
  # successors.
  # ----------------------------------------------------------------------
  def updateOutput(s, i, j, value):
    s.output_value[i][j] = value

  def updateInput(s, value):
    s.input_value[s.current_input_index] = value
    s.current_input_index += 1
    if s.current_input_index == s.num_input:
      s.current_input_index = 0

  def update_predicate(s, predicate):
    s.input_predicate = predicate

def get_node(node_id, nodes):
  for node in nodes:
    if node.id == node_id:
      return node
  return None

class DFG:

  def __init__(s, json_file_name, const_list, data_spm):
    s.nodes = []
    s.id2node_map = {}
    s.num_const = 0
    s.num_input = 0
#    s.num_output  = 0
    # We assume single liveout for now
    s.num_liveout = 1
    s.const_list = const_list
    s.data_spm = data_spm
    with open(json_file_name) as json_file:
      dfg = json.load(json_file)
      for i in range(len(dfg)):
        print("[cheng] check dfg[i]['fu']: ", dfg[i]['fu'] )
        node = Node(dfg[i]['id'],
                    # getUnitType(dfg[i]['fu']),
                    # getOptType(dfg[i]['opt']),
                    dfg[i]['fu'],
                    dfg[i]['opt'],
                    dfg[i]['opt_predicate'],
                    dfg[i]['in_const'],
                    dfg[i]['in'],
                    dfg[i]['in_predicate'],
                    dfg[i]['out'])
        s.nodes.append(node)
        s.id2node_map[node.id] = node
        max_layer = -1
        print("cur_node: ", node.id, " pre: ", (node.input_node_ids+node.input_predicate_node))
        for input_node in (node.input_node_ids+node.input_predicate_node):
          pre_node = get_node(input_node, s.nodes)
          if(pre_node != None):
            if pre_node.layer > max_layer:
              max_layer = pre_node.layer
        node.layer = max_layer + 1
          
        s.num_const  += node.num_const
        s.num_input  += node.num_inputs
#        s.num_output += node.num_output
        if 'live_out_ctrl' in dfg[i].keys():
          node.live_out_ctrl = 1
        if 'live_out_val' in dfg[i].keys():
          node.live_out_val = 1

    s.layer_diff_list = [0] * s.num_input
    channel_index= 0
    for node in s.nodes:
      for node_id in node.input_node_ids:
        layer_diff = node.layer - get_node(node_id, s.nodes).layer
        if layer_diff > 0:
          s.layer_diff_list[channel_index] = layer_diff
        else:
          s.layer_diff_list[channel_index] = 1
        channel_index += 1

    # Constructs the nodes dependency.
    s.construct_dependency()

    # Orders the nodes in topological ordering.
    s.order_in_topological()

  def construct_dependency(s):
    print("[INFO] Constructs the nodes dependency.")
    for node in s.nodes:
      for input_node_id in node.input_node_ids:
        input_node = id2node_map[input_node_id]
        node.input_nodes.append(input_node)
        input_node.output_nodes.append(node)

    # Double-checks the number of inputs/outputs are consistent.
    for node in s.nodes:
      assert(node.num_inputs == len(node.input_nodes))
      assert(node.num_inputs == len(node.input_node_ids))
      assert(node.num_outputs == len(node.output_nodes))
      assert(node.num_outputs == len(node.output_node_ids))

  def order_in_topological(s):
    print( "[INFO] Orders nodes in topological ordering." )
    s.levels_of_nodes = []
    s.sorted_nodes = []
    pending_sorting_nodes = deque()
    visited_nodes = set()
    for node in s.nodes:
      if node.opt == "OPT_PHI_START" or node.num_inputs == 0:
        pending_sorting_nodes.append(node)
        visited_nodes.add(node)

    # There should be one starting point at least.
    assert(len(visited_nodes) > 0)

    level = 0
    while len(pending_sorting_nodes) > 0:
      nodes_in_current_level = []
      pending_sorting_num_of_nodes = len(pending_sorting_nodes)
      while pending_sorting_num_of_nodes > 0:
        node = pending_sorting_nodes.pop_left()
        node.update_level(level)
        # 
        s.sorted_nodes.append(node)
        nodes_in_current_level.append(node)
        pending_sorting_num_of_nodes -= 1

        # Adds the pending nodes into the queue.
        for successor_node in node.output_nodes:
          visited_all_predecessors = True
          for predecessor_node in successor_node.input_nodes:
            if predecessor_node not in visited_nodes or
               predecessor_node in pending_sorting_num_of_nodes:
              visited_all_predecessors = False
          if visited_all_predecessors and
             successor_node not in visited_nodes:
            visited_nodes.add(successor_node)
            pending_sorting_nodes.append(successor_node)
      s.levels_of_nodes.append(nodes_in_current_level)
      level += 1

  def get_node( s, node_id ):
    return get_node( node_id, s.nodes)

