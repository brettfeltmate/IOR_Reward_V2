from klibs.KLIndependentVariable import IndependentVariableSet

IOR_Reward_V2_ind_vars = IndependentVariableSet()

IOR_Reward_V2_ind_vars.add_variable("cue_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("probe_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("probe_colour", str, ["high", "low", "neutral", "catch"])
IOR_Reward_V2_ind_vars.add_variable("high_value_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("winning_bandit", str, ["high", "low"])