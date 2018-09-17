from klibs.KLIndependentVariable import IndependentVariableSet

IOR_Reward_V2_ind_vars = IndependentVariableSet()

IOR_Reward_V2_ind_vars.add_variable("high_value_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("cue_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("winning_bandit", str, ["high", "high", "high", "low", "low", "low", "lose", "lose"])
IOR_Reward_V2_ind_vars.add_variable("probe_location", str, ["left", "right"])
IOR_Reward_V2_ind_vars.add_variable("probe_colour", str, ["high", "low", "neutral"])
IOR_Reward_V2_ind_vars.add_variable("go_no_go", str, ["go","nogo"])
