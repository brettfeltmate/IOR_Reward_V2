# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

# Import required KLibs classes & functions.
import klibs
from klibs import P
from klibs.KLConstants import *
from klibs.KLExceptions import TrialException
from klibs.KLUtilities import deg_to_px
from klibs.KLKeyMap import KeyMap
from klibs.KLTime import CountDown
from klibs.KLUserInterface import ui_request, any_key, key_pressed
from klibs.KLGraphics import flip, blit, fill, clear
from klibs.KLGraphics.colorspaces import const_lum
from klibs.KLGraphics.KLDraw import Rectangle, Asterisk, Ellipse, FixationCross
from klibs.KLCommunication import message, user_queries, query
from klibs.KLResponseCollectors import ResponseCollector
from klibs.KLEventInterface import TrialEventTicket as ET

# Import additional required libraries
import random
import sdl2

# Define some useful constants
LEFT = "left"
RIGHT = "right"
PROBE = "probe"
BANDIT = "bandit"
HIGH = "high"
LOW = "low"
NEUTRAL = "neutral"
GO = "go"
NOGO = "nogo"
YES = "yes"
NO = "no"

# Define colours for the experiment
WHITE = [255, 255, 255, 255]
GREY = [100, 100, 100, 255]
BLACK = [0, 0, 0, 255]
BLUE = [0, 0, 255, 255]
RED = [255, 0, 0, 255]
GREEN = [0, 255, 0, 255]
PURPLE = [95, 25, 130, 255]
PASTEL_GREEN = [75, 210, 100, 255]
PASTEL_RED = [210, 75, 75, 255]

class IOR_Reward_V2(klibs.Experiment):

	def setup(self):

		# Stimulus sizes
		thick_rect_border = deg_to_px(0.5)
		thin_rect_border = deg_to_px(0.1)
		star_size = deg_to_px(0.6)
		star_thickness = deg_to_px(0.1)
		square_size = deg_to_px(3)
		large_text_size = 0.65

		# Stimulus drawbjects
		self.thick_rect = Rectangle(square_size, stroke=[thick_rect_border, WHITE, STROKE_CENTER])
		self.thin_rect = Rectangle(square_size, stroke=[thin_rect_border, WHITE, STROKE_CENTER])
		self.neutral_box = self.thin_rect.render()

		self.star = Asterisk(star_size, star_thickness, fill=WHITE)
		self.star_cueback = Asterisk(star_size*2, star_thickness*2, fill=WHITE)
		self.star_muted = Asterisk(star_size, star_thickness, fill=GREY)

		self.go = FixationCross(star_size, star_thickness, fill=BLACK)
		self.go.render()
		self.nogo = FixationCross(star_size, star_thickness, fill=BLACK, rotation=45)
		self.nogo.render()

		self.left_bandit = Ellipse(int(0.75 * square_size))
		self.right_bandit = Ellipse(int(0.75 * square_size))
		self.probe = Ellipse(int(0.75 * square_size))

		# Layout
		box_offset = deg_to_px(8.0)
		self.left_box_loc = (P.screen_c[0] - box_offset, P.screen_c[1])
		self.right_box_loc = (P.screen_c[0] + box_offset, P.screen_c[1])

		# Set cotoa
		self.cotoa = 800 # ms

		self.feedback_exposure_period = 1.25 # sec

		# Bandit payout variables
		self.high_payout_baseline = 12
		self.low_payout_baseline = 8
		self.total_score = None
		self.penalty = -5
		
		# Generate colours from colour wheel
		self.target_colours = [const_lum[0], const_lum[120], const_lum[240]]
		random.shuffle(self.target_colours)

		# Assign to bandits & neutral probe
		self.high_value_colour = self.target_colours[0]
		self.low_value_colour = self.target_colours[1]
		self.neutral_value_colour = self.target_colours[2]

		# EyeLink Boundaries
		fix_bounds = [P.screen_c, square_size/2]
		self.el.add_boundary('fixation', fix_bounds, CIRCLE_BOUNDARY)

		# Initialize response collectors
		self.probe_rc = ResponseCollector(uses=RC_KEYPRESS)
		self.bandit_rc = ResponseCollector(uses=RC_KEYPRESS)
		
		# Initialize ResponseCollector keymaps
		self.bandit_keymap = KeyMap(
			'bandit_response', # Name
			['z', '/'], # UI labels
			["left", "right"], # Data labels
			[sdl2.SDLK_z, sdl2.SDLK_SLASH] # SDL2 Keysyms
		)
		self.probe_keymap = KeyMap(
			'probe_response',
			['spacebar'],
			["pressed"],
			[sdl2.SDLK_SPACE]
		)

		# Experiment Messages
		self.txtm.add_style("score up", large_text_size, PASTEL_GREEN)
		self.txtm.add_style("score down", large_text_size, PASTEL_RED)
		self.txtm.add_style("timeout", large_text_size, WHITE)

		err_txt = "{0}\n\nPress any key to continue."
		lost_fixation_txt = err_txt.format("Eyes moved! Please keep your eyes on the asterisk.")
		probe_timeout_txt = err_txt.format("No response detected! Please respond as fast and as accurately as possible.")
		bandit_timeout_txt = err_txt.format("Bandit selection timed out!")
		response_on_nogo_txt = err_txt.format("\'nogo\' signal (x) presented\nPlease only respond when you see "
			"the \'go\' signal (+).")
		
		self.err_msgs = {
			'fixation': message(lost_fixation_txt, align='center', blit_txt=False),
			'probe_timeout': message(probe_timeout_txt, 'timeout', align='center', blit_txt=False),
			'bandit_timeout': message(bandit_timeout_txt, 'timeout', align='center', blit_txt=False),
			'response_on_nogo': message(response_on_nogo_txt, align='center', blit_txt=False)
		}

		self.rest_break_txt = err_txt.format("Whew! that was tricky eh? Go ahead and take a break before continuing.")
		self.end_of_block_txt = "You're done the first task! Please buzz the researcher to let them know!"
		
		# Insert bandit block
		if P.run_practice_blocks:
			self.insert_practice_block(1, trial_counts=P.trials_bandit_block)
	
	def block(self):
		
		# Block type defaults to probe trials, overidden in practice block(s)
		self.block_type = PROBE

		# Show total score following completion of bandit task
		if self.total_score:
			fill()
			score_txt = "Total block score: {0} points!".format(self.total_score)
			msg = message(score_txt, 'timeout', blit_txt=False)
			blit(msg, 5, P.screen_c)
			flip()
			any_key()

		self.total_score = 0 # Reset score once presented
		
		# Bandit task
		if P.practicing:
			self.block_type == BANDIT
			# Initialize selection counters
			self.times_selected_high = 0
			self.time_selected_low = 0

		# End of block messaging
		if not P.practicing:
			fill()
			msg = message(self.end_of_block_txt,blit_txt=False)
			blit(msg, 5, P.screen_c)
			flip()
			any_key()

	def setup_response_collector(self):
				
		# Configure probe response collector
		self.probe_rc.terminate_after = [1500, TK_MS]
		self.probe_rc.display_callback = self.probe_callback
		self.probe_rc.flip = True
		self.probe_rc.keypress_listener.key_map = self.probe_keymap
		self.probe_rc.keypress_listener.interrupts = True
		
		# Configure bandit response collector
		self.bandit_rc.terminate_after = [1500, TK_MS]
		self.bandit_rc.display_callback = self.bandit_callback
		self.bandit_rc.flip = True
		self.bandit_rc.keypress_listener.key_map = self.bandit_keymap
		self.bandit_rc.keypress_listener.interrupts = True

	def trial_prep(self):
		# Reset error flag
		self.targets_shown = False
		self.err = None

		# BANDIT PROPERTIES
		if P.practicing:
			self.cotoa = 'NA'
			# Establish location & colour of bandits

			if self.high_value_location == LEFT:
				self.left_bandit.fill = self.high_value_colour
				self.right_bandit.fill = self.low_value_colour
				self.low_value_location = RIGHT
			else:
				self.left_bandit.fill = self.low_value_colour
				self.right_bandit.fill = self.high_value_colour
				self.low_value_location = LEFT
			self.left_bandit.render()
			self.right_bandit.render()
		
		# PROBE PROPERTIES
		else:
			# Rest breaks
			if P.trial_number % (P.trials_per_block/P.breaks_per_block) == 0:
				if P.trial_number < P.trials_per_block:
					fill()
					msg = message(self.rest_break_txt, 'timeout', blit_txt=False)
					blit(msg, 5, P.screen_c)
					flip()
					any_key()

			# Establish & assign probe location
			self.probe_loc = self.right_box_loc if self.probe_location == RIGHT else self.left_box_loc
			# go/nogo signal always presented w/probe
			self.go_nogo_loc = self.probe_loc	

			# Establish & assign probe colour
			if self.probe_colour == HIGH:
				self.probe.fill = self.high_value_colour
			elif self.probe_colour == LOW:
				self.probe.fill = self.low_value_colour
			else:
				self.probe.fill = self.neutral_value_colour
			self.probe.render()

		# Add timecourse of events to EventManager
		if P.practicing: # Bandit trials
			events = [[1000, 'target_on']]
		else: # Probe trials
			events = [[1000, 'cue_on']]
			events.append([events[-1][0] + 200, 'cue_off'])
			events.append([events[-1][0] + 200, 'cueback_off'])
			events.append([events[-2][0] + 800, 'target_on'])
		for e in events:
			self.evm.register_ticket(ET(e[1], e[0]))

		# Perform drift correct on Eyelink before trial start
		self.el.drift_correct()

	def trial(self):
		
		# BANDIT TRIAL
		if P.practicing:
			cotoa, probe_rt = ['NA', 'NA'] # Don't occur in bandit blocks

			# Present placeholders
			while self.evm.before('target_on', True) and not self.err:
				self.confirm_fixation()
				self.present_neutral_boxes() 
				flip()

			# BANDIT RESPONSE PERIOD
			self.targets_shown = True # After bandits shown, don't recycle trial
			
			# Present bandits and listen for response
			self.bandit_rc.collect()
			
			# If wrong response made
			if self.err:
				bandit_choice, bandit_rt, reward = ['NA', 'NA', 'NA']
			else:
				self.err = 'NA'
				# Retrieve responses from ResponseCollector(s) & record data
				bandit_choice = self.bandit_rc.keypress_listener.response(value=True, rt=False)
				bandit_rt = self.bandit_rc.keypress_listener.response(value=False, rt=True)

				if bandit_rt == TIMEOUT:
					self.show_error_message('bandit_timeout')
					reward = 'NA'
				else:
					# Determine bandit payout & display
					reward = self.feedback(bandit_choice)

		# PROBE TRIAL
		else:
			bandit_choice, bandit_rt, reward = ['NA', 'NA', 'NA'] # Don't occur in probe trials

			# Present placeholders & confirm fixation
			while self.evm.before('target_on', True):
				self.confirm_fixation()
				self.present_neutral_boxes()

				# Present cue
				if self.evm.between('cue_on', 'cue_off'):
					if self.cue_location == LEFT:
						blit(self.thick_rect, 5, self.left_box_loc)
					else:
						blit(self.thick_rect, 5, self.right_box_loc)
				# Present cueback
				elif self.evm.between('cue_off', 'cueback_off'):
					blit(self.star_cueback, 5, P.screen_c)

				flip()

			# PROBE RESPONSE PERIOD
			self.targets_shown = True # After probe shown, don't recycle trial
			# Present probes & listen for response
			self.probe_rc.collect()

			# If 'go' trial, check for response
			if self.go_no_go == GO:
				# If wrong response made
				if self.err:
					probe_rt = 'NA'
				# If correct response OR timeout
				else:
					self.err = 'NA'
					probe_rt = self.probe_rc.keypress_listener.response(value=False,rt=True)
					if probe_rt == TIMEOUT:
						self.show_error_message('probe_timeout')
						probe_rt = 'NA'
			# Similarly, for 'nogo' trials
			else:
				probe_rt = 'NA'
				# If response made, penalize
				if len(self.probe_rc.keypress_listener.responses):
					self.show_error_message('response_on_nogo')
					self.err = 'response_on_nogo'
				# If no response, continue as normal
				else:
					self.err = 'NA'
		# Return trial data
		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"block_type": "BANDIT" if P.practicing else "PROBE",
			"high_value_col": self.high_value_colour[:3] if P.practicing else 'NA',
			"high_value_loc": self.high_value_location if P.practicing else 'NA',
			"low_value_col": self.low_value_colour[:3] if P.practicing else 'NA',
			"low_value_loc": self.low_value_location if P.practicing else 'NA',
			"winning_trial": self.winning_trial if P.practicing else 'NA',
			"bandit_selected": self.bandit_selected if P.practicing else 'NA',
			"bandit_rt": bandit_rt,
			"reward": reward,
			"cue_loc": self.cue_location if not P.practicing else 'NA',
			"cotoa": 1000 if not P.practicing else 'NA',
			"probe_loc": self.probe_location if not P.practicing else 'NA',
			"probe_col": self.probe_colour if not P.practicing else 'NA',
			"go_no_go": self.go_no_go if not P.practicing else 'NA',
			"probe_rt": probe_rt,
			"err": self.err
		}
		# Clear remaining stimuli from screen
		clear()

	def trial_clean_up(self):
		# Clear responses from responses collectors before next trial
		self.probe_rc.keypress_listener.reset()
		self.bandit_rc.keypress_listener.reset()


	def clean_up(self):
		# Let Ss know when experiment is over
		self.all_done_text = "You're all done! Now I get to take a break.\nPlease buzz the researcher to let them know you're done!"
		fill()
		msg = message(self.all_done_text, 'timeout', blit_txt=False)
		blit(msg, 5, P.screen_c)
		flip()
		any_key()

	# Determines & presents feedback
	def feedback(self, response):

		# Keep count of bandit choices
		if response == self.high_value_location:
			self.bandit_selected = HIGH
			self.times_selected_high = self.times_selected_high + 1
			# Occasionally probe participant learning
			if self.times_selected_high in [5,10,15]:
				self.query_learning(HIGH)

		else:
			self.bandit_selected = LOW
			self.time_selected_low = self.time_selected_low + 1
			if self.time_selected_low in [5,10,15]:
				self.query_learning(LOW)
		
		# Determine payout
		if self.winning_trial == YES:
			points = self.bandit_payout(value=self.bandit_selected)
			msg = message("You won {0} points!".format(points), "score up", blit_txt=False)
		else:
			points = self.penalty # -5
			msg = message("You lost 5 points!", "score down", blit_txt=False)
		
		# Running point total
		self.total_score += points
		feedback = [points, msg]

		# Present payout
		feedback_exposure = CountDown(self.feedback_exposure_period)
		while feedback_exposure.counting():
			ui_request()
			fill()
			blit(feedback[1], location=P.screen_c, registration=5)
			flip()
			
		return feedback[0]

	# Calculates bandit payout
	def bandit_payout(self, value):
		mean = self.high_payout_baseline if value == HIGH else self.low_payout_baseline
		# sample from normal distribution with sd of 1 and round to nearest int
		return int(random.gauss(mean, 1) + 0.5)
	
	# Confirms whether Ss are fixating
	def confirm_fixation(self):
		if not self.el.within_boundary('fixation', EL_GAZE_POS):
			self.show_error_message('fixation')
			if self.targets_shown:
				self.err = 'left_fixation'
			else:
				raise TrialException('gaze left fixation') # recycle trial
	
	# Presents error messages
	def show_error_message(self, msg_key):
		fill()
		blit(self.err_msgs[msg_key], location=P.screen_c, registration=5)
		flip()
		any_key()

	# Utility function to generate random time intervals with a given range
	# that are multiples of the current refresh rate (e.g. 16.7ms for a 60Hz monitor)
	def random_interval(self, lower, upper):
		min_flips = int(round(lower/P.refresh_time))
		max_flips = int(round(upper/P.refresh_time))
		return random.choice(range(min_flips, max_flips+1, 1)) * P.refresh_time

	# Presents neutral boxes, duh
	def present_neutral_boxes(self):
		fill()
		blit(self.star, 5, P.screen_c)
		blit(self.neutral_box, 5, self.left_box_loc)
		blit(self.neutral_box, 5, self.right_box_loc)
			
	# Presents bandits
	def bandit_callback(self, before_go=False):
		self.confirm_fixation()
		self.present_neutral_boxes()

		blit(self.left_bandit, 5, self.left_box_loc)
		blit(self.right_bandit, 5, self.right_box_loc)

	# Presents probes	
	def probe_callback(self):
		self.confirm_fixation()
		self.present_neutral_boxes()

		# Present probe & go/nogo stimulus
		if self.go_no_go == GO:
			blit(self.probe, 5, self.probe_loc)
			blit(self.go, 5, self.probe_loc)
		else:
			blit(self.probe, 5, self.probe_loc)
			blit(self.nogo, 5, self.probe_loc)

	# Assesses learning by asking Ss their anticipated trial earnings
	def query_learning(self, bandit):
		if bandit == HIGH:
			anticipated_reward_high = query(user_queries.experimental[0])
			anticipated_reward_survey = {
				'participant_id': P.participant_id,
				'anticipated_reward_high': anticipated_reward_high,
				'anticipated_reward_low': "NA"
			}
		else:
			anticipated_reward_low = query(user_queries.experimental[1])
			anticipated_reward_survey = {
				'participant_id': P.participant_id,
				'anticipated_reward_high': "NA",
				'anticipated_reward_low': anticipated_reward_low
			}

		self.db.insert(anticipated_reward_survey, table='surveys')