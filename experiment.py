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

		# Timing
		# cotoa = cue-offset target-onset asynchrony
		self.cotoa_min = 700 # ms
		self.cotoa_max = 1000 # ms
		self.feedback_exposure_period = 1.25 # sec

		# Bandit payout variables
		self.high_payout_baseline = 12
		self.low_payout_baseline = 8
		self.total_score = None
		self.penalty = -5
		
		# Generate colours from colour wheel
 		self.colour_combos = []
		for angle in [0, 45, 90, 135]:
			combo = [const_lum[angle], const_lum[angle+180]]
			self.colour_combos.append(combo)
		random.shuffle(self.colour_combos)

		# EyeLink Boundaries
		fix_bounds = [P.screen_c, square_size/2]
		self.el.add_boundary('fixation', fix_bounds, CIRCLE_BOUNDARY)

		# Do we want to continue using audio responses?
		# Do we want to monitor for wrong response types? To both targets?
		# Do we want to calibrate audio listener before bandit blocks? Would this confuse subj's?
		self.probe_rc = ResponseCollector(uses=[RC_AUDIO, RC_KEYPRESS])
		self.bandit_rc = ResponseCollector(uses=[RC_KEYPRESS])
		
		# Initialize ResponseCollector keymap
		self.keymap = KeyMap(
			'bandit_response', # Name
			['z', '/'], # UI labels
			["left", "right"], # Data labels
			[sdl2.SDLK_z, sdl2.SDLK_SLASH] # SDL2 Keysyms
		)

		# Experiment Messages
		self.txtm.add_style("score up", large_text_size, PASTEL_GREEN)
		self.txtm.add_style("score down", large_text_size, PASTEL_RED)
		self.txtm.add_style("timeout", large_text_size, WHITE)

		err_txt = "{0}\n\nPress any key to continue."
		lost_fixation_txt = err_txt.format("Eyes moved! Please keep your eyes on the asterisk.")
		probe_timeout_txt = err_txt.format("No response detected! Please answer louder or faster.")
		bandit_timeout_txt = err_txt.format("Bandit selection timed out!")
		wrong_response_txt = err_txt.format("Wrong response type!\nPlease make vocal responses "
			"to probes and keypress responses to bandits.")
		response_on_nogo_txt = err_txt.format("\'nogo\' signal (x) presented\nPlease only respond when you see "
			"the \'go\' signal (+).")
		
		self.err_msgs = {
			'fixation': message(lost_fixation_txt, align='center', blit_txt=False),
			'probe_timeout': message(probe_timeout_txt, 'timeout', align='center', blit_txt=False),
			'bandit_timeout': message(bandit_timeout_txt, 'timeout', align='center', blit_txt=False),
			'wrong_response': message(wrong_response_txt, align='center', blit_txt=False),
			'response_on_nogo': message(response_on_nogo_txt, align='center', blit_txt=False)
		}
		
		# Insert bandit block preceeding every probe block
		if P.run_practice_blocks:
			self.insert_practice_block(1, trial_counts=P.trials_bandit_block)
	
	def block(self):
		
		# Block type defaults to probe trials, overidden in practice block(s)
		self.block_type = PROBE

		# At end of 'practice' block, show Ss their total score
		if self.total_score:
			fill()
			score_txt = "Total block score: {0} points!".format(self.total_score)
			msg = message(score_txt, 'timeout', blit_txt=False)
			blit(msg, 5, P.screen_c)
			flip()
			any_key()
		
		# So that scores aren't presented after bandit block is completed
		# Yes, I know, there's a better way; but this works and I'm lazy
		self.total_score = 0

		# Note: Ss only experience one 'practice' block, wherein they perform a 2-armed bandit task
		# intended to induce value associations to the bandit colours 
		if P.practicing:
			self.block_type == BANDIT
			# Randomly select bandit colours from list generated at setup
			bandit_colours = self.colour_combos.pop()
			random.shuffle(bandit_colours)
			# Assign to high/low bandit
			self.high_value_color = bandit_colours[0]
			self.low_value_color = bandit_colours[1]
			# Store remaining colours to be used as probe colours
			self.probe_colours = [item for sublist in self.colour_combos for item in sublist]

			self.times_selected_high = 0
			self.time_selected_low = 0

		# Calibrate microphone for audio responses
		if not P.practicing:
			self.probe_rc.audio_listener.threshold = self.audio.calibrate()

	def setup_response_collector(self):
				
		# Configure probe response collector
		self.probe_rc.terminate_after = [1500, TK_MS]
		self.probe_rc.display_callback = self.probe_callback
		self.probe_rc.flip = True
		self.probe_rc.keypress_listener.key_map = self.keymap
		# Listen for errant keypress responses to probes
		self.probe_rc.keypress_listener.interrupts = True
		self.probe_rc.audio_listener.interrupts = True
		
		# Configure bandit response collector
		self.bandit_rc.terminate_after = [1500, TK_MS]
		self.bandit_rc.display_callback = self.bandit_callback
		self.bandit_rc.flip = True
		self.bandit_rc.keypress_listener.key_map = self.keymap
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
				self.left_bandit.fill = self.high_value_color
				self.right_bandit.fill = self.low_value_color
				self.low_value_location = RIGHT
			else:
				self.left_bandit.fill = self.low_value_color
				self.right_bandit.fill = self.high_value_color
				self.low_value_location = LEFT
			self.left_bandit.render()
			self.right_bandit.render()
		
		# PROBE BLOCK
		else:
			# Randomly choose COTOA on each trial
			self.cotoa = self.random_interval(self.cotoa_min, self.cotoa_max)

			# Establish probe location
			self.probe_loc = self.right_box_loc if self.probe_location == RIGHT else self.left_box_loc
			self.go_nogo_loc = self.probe_loc	

			# Establish probe colour
			if self.probe_colour == HIGH:
				self.probe.fill = self.high_value_color
			elif self.probe_colour == LOW:
				self.probe.fill = self.low_value_color
			else:
				# Randomly select 'neutral' (no value association) colour
				self.probe.fill = random.choice(self.probe_colours)
			self.probe.render()

		# Add timecourse of events to EventManager
		if P.practicing:
			events = [[1000, 'target_on']]
		else:
			events = [[1000, 'cue_on']]
			events.append([events[-1][0] + 200, 'cue_off'])
			events.append([events[-1][0] + 200, 'cueback_off'])
			events.append([events[-2][0] + self.cotoa, 'target_on'])
		for e in events:
			self.evm.register_ticket(ET(e[1], e[0]))

		# Perform drift correct on Eyelink before trial start
		self.el.drift_correct()

	def trial(self):
		
		# BANDIT BLOCK
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

		# PROBE BLOCK
		else:
			bandit_choice, bandit_rt, reward = ['NA', 'NA', 'NA'] # Don't occur in probe trials

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
				# If wrong response type
				if len(self.probe_rc.keypress_listener.responses):
					self.show_error_message('wrong_response')
					self.err = 'keypress_on_probe'
				# If no response collected
				elif len(self.probe_rc.audio_listener.responses) == 0:
					self.show_error_message('probe_timeout')
					# If mic craps out
					if self.probe_rc.audio_listener.stream_error:
						self.err = 'microphone_error'
					# Otherwise, timeout
					else:
						self.err = 'probe_timeout'
			# If response made on 'nogo' trial
			else:
				if len(self.probe_rc.keypress_listener.responses) or len(self.probe_rc.audio_listener.responses):
					self.show_error_message('response_on_nogo')
					self.err = 'response_on_nogo'
			
			# If error in repsonse, don't record reaction time
			if self.err:
				probe_rt = 'NA'	
			else:
				self.err = 'NA'
				# Retrieve responses from ResponseCollector & record data
				probe_rt = self.probe_rc.audio_listener.response(value=False, rt=True)

		# Clear remaining stimuli from screen before trial end
		clear()

		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"block_type": self.block_type,
			"high_value_col": self.high_value_color[:3] if self.block_type == BANDIT else 'NA',
			"low_value_col": self.low_value_color[:3] if self.block_type == BANDIT else 'NA',
			"winning_bandit": self.winning_bandit if self.block_type == BANDIT else 'NA',
			"bandit_choice": bandit_choice,
			"bandit_rt": bandit_rt,
			"reward": reward,
			"cue_loc": self.cue_location if self.block_type == PROBE else 'NA',
			"cotoa": self.cotoa if self.block_type == PROBE else 'NA',
			"probe_loc": self.probe_location if self.block_type == PROBE else 'NA',
			"probe_col": self.probe_colour if self.block_type == PROBE else 'NA',
			"go_no_go": self.go_no_go if self.block_type == PROBE else 'NA',
			"probe_rt": probe_rt,
			"err": self.err
		}

	def trial_clean_up(self):
		# Clear responses from responses collectors before next trial
		self.probe_rc.audio_listener.reset()
		self.probe_rc.keypress_listener.reset()
		self.bandit_rc.keypress_listener.reset()


	def clean_up(self):
		pass

	def feedback(self, response):
		# Determine winning bandit
		if self.winning_bandit == HIGH:
			winning_bandit_loc = self.high_value_location
		else:
			winning_bandit_loc = self.low_value_location

		# Keep count of bandit choices
		if response == self.high_value_location:
			self.times_selected_high = self.times_selected_high + 1
			# Occasionally probe participant learning
			if self.times_selected_high in [5,10,15]:
				self.query_learning(HIGH)

		else:
			self.time_selected_low = self.time_selected_low + 1
			if self.time_selected_low in [5,10,15]:
				self.query_learning(LOW)
		
		# Determine payout
		if response == winning_bandit_loc:

			points = self.bandit_payout(value=self.winning_bandit)
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

	def confirm_fixation(self):
		if not self.el.within_boundary('fixation', EL_GAZE_POS):
			self.show_error_message('fixation')
			if self.targets_shown:
				self.err = 'left_fixation'
			else:
				raise TrialException('gaze left fixation') # recycle trial

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

		#probe_loc = self.right_box_loc if self.probe_location == RIGHT else self.left_box_loc

		# Present probe & go/nogo stimulus
		if self.go_no_go == GO:
			blit(self.probe, 5, self.probe_loc)
			blit(self.go, 5, self.probe_loc)
		else:
			blit(self.probe, 5, self.probe_loc)
			blit(self.nogo, 5, self.probe_loc)

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