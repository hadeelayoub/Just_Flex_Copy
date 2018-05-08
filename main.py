#!/usr/bin/python


# !!! NOTE FOR TIRED SELF !!!
# Uncomment lines to return websockets functionality:
# 70, 176, 177, 211, 274


"""
__author__    = "Leon Fedden"

"""

from state   import State
from fps     import Fps
from fastdtw import fastdtw
import gaugette.ssd1306
import time
import sys
import scipy.interpolate as interp
import numpy as np
import math
import uuid
from socketIO_client import SocketIO, LoggingNamespace
import json
import logging
import os.path

# Gesture recording state.
current_label   = 0
current_gesture = []

if os.path.isfile("uuids.npy"):
    print "loaded from file"
    all_gestures = np.load('features.npy').tolist()
    all_labels   = np.load('labels.npy').tolist()
    all_uuids    = np.load('uuids.npy').tolist()
    all_times    = np.load('times.npy').tolist()

else:

    all_gestures    = []
    all_labels      = []
    all_uuids       = []
    all_times       = []

gesture_size    = 10

# Making sure we don't record gestures that are too 
# small. 
min_gesture_size = 7

# Where the buttons are plugged into the pi.
button_1_pin = 5   # Red.
button_2_pin = 21  # Black.

# Instanciate the state object.
state_management = State(button_1_pin, button_2_pin)

# Instanciate the object controlling our desired fps.
desired_fps = 8
fps_timer = Fps(desired_fps)

# Are we recording or classifying gestures?
record_mode = False

# Classification stuff.
amount_neighbours = 1

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

# Websockets 
socketIO = SocketIO('http://brightsigndemo.eu-gb.mybluemix.net', 80, LoggingNamespace)

# OLED screen stuff
RESET_PIN = 15
DC_PIN = 16
led = gaugette.ssd1306.SSD1306(reset_pin=RESET_PIN, dc_pin=DC_PIN)
led.begin()
led.clear_display()

#======================================================

def idle(self):
    """ Method called when glove is below threshold
    of movement for recording.

    The self is needed in order to bind this method
    to the private method of State. Perhaps set the
    label of the future recordings here.

    """
    if record_mode:
        r = "record mode (CLASS " + str(current_label) + ")"
    else:
        r = "classify mode"
    print "idle: " + r

#======================================================

def recording(self):
    """ This method is called each frame of the loop
    when the glove is above the threshold of moving
    for recording.

    Record the sensor data here.

    """
    global current_gesture
    global state_management
    data = state_management.get_sensor_data()
    print data[0:5]

    # Have we got eight elements?
    #assert len(data[-8:]) == 8
    current_gesture.append(data[0:5])
    #print "RECORDING"

#======================================================
def generate_model():
    """ This method is called once when the recording mode
    changes to false and the program is in classification
    mode.

    This is so the model can be reduced to one gesture per
    label to save time in the classification stage.
    """

    global all_gestures
    global all_labels
    global gesture_size
    global all_uuids
    global all_times
    new_labels = []
    new_uuids = []
    unique_labels = np.unique(all_labels)
    new_gestures = []
    new_dates = []

    for label in unique_labels:
        this_gesture_amount = 0
        empty_gesture = [[0.0 for _ in range(5)] for _ in range(gesture_size)]
        this_labels_gesture = np.array(empty_gesture)

        needs_uuid = False
        current_uuid_index = None

        dates = []
        for j, gesture in enumerate(all_gestures):
            if all_labels[j] == label:
                this_labels_gesture += np.array(gesture)
                this_gesture_amount += 1
                dates.append(all_times[j])
                current_uuid_index = j

                if j >= len(all_uuids):
                    needs_uuid = True

        dates.sort()
        index = len(dates) - 1
        oldest_date = dates[index]
        new_dates.append(oldest_date)

        this_labels_gesture /= this_gesture_amount
        new_labels.append(label)
        new_gestures.append(this_labels_gesture.tolist())

        if needs_uuid:
            uid = str(uuid.uuid4())
            new_uuids.append(uid)
        else:
            new_uuids.append(all_uuids[current_uuid_index])

    all_gestures = new_gestures
    all_labels = new_labels
    all_times = new_dates
    all_uuids = new_uuids
    assert len(all_labels) == len(all_times) and len(all_uuids) == len(all_labels) and len(all_gestures) == len(all_labels)
    data_to_send = []
    for i, iduu in enumerate(all_uuids):
        data_to_send.append( {"id" : iduu, "date" : all_times[i] } )

    socketIO.emit('state', data_to_send)
    socketIO.wait(seconds=1)

    np_labels = np.asarray(all_labels)
    np.savetxt("l.csv", np_labels, delimiter=",")
    np.set_printoptions(threshold=np.inf, linewidth=np.inf)
    with open("g.csv", 'w') as f:
        f.write(np.array2string(np.asarray(all_gestures), separator=','))

    print len(all_labels)
    print all_labels

#======================================================
def euc(a, b):
    """Euclidean distance passed to FastDTW in recorded()"""
    distance = 0
    for i in range(len(a)):
        distance += pow(a[i] - b[i], 2)
    return math.sqrt(distance)

def recorded(self):
    """ This method is called once when the recording
    has finished.

     The loop will then resume in an idle state.
    """
    global current_gesture
    global min_gesture_size

    global all_gestures
    global all_labels
    global record_mode
    global amount_neighbours
    global gesture_size
    global socketIO

    # Are we recording or classifying?
    if record_mode == True:

        warped_gesture = []
        transposed_gesture = [list(i) for i in zip(*current_gesture)]
        for i, feature in enumerate(transposed_gesture):

            feature_array  = np.array(feature)
            feature_interp = interp.interp1d(np.arange(feature_array.size), feature_array)
            feature_warped = feature_interp(np.linspace(0, feature_array.size-1, gesture_size))
            warped_gesture.append(feature_warped.tolist())

        current_gesture = [list(i) for i in zip(*warped_gesture)]

        if len(current_gesture) > min_gesture_size:
            all_gestures.append(current_gesture)
            all_labels.append(current_label)
            all_times.append(time.time())
        else:
            print "Gesture size too small!"
    elif len(all_gestures) > 0 and len(current_gesture) > min_gesture_size:

        # We store tuples of our distances and labels here
        distances = []

        for i in range(len(all_gestures)):
            time_series_1 = np.array(current_gesture, dtype='float')
            time_series_2 = np.array(all_gestures[i], dtype='float')
            print time_series_2.shape
            print time_series_1.shape
            distance, path = fastdtw(time_series_1,
                                     time_series_2,
                                     dist=euc)
            # Packing the label and distance.
            distance_tuple = (all_labels[i], distance)

            distances.append(distance_tuple)

        distances.sort(key=lambda tup: tup[1])
        unique_labels = set(all_labels)
        amount_gestures = len(unique_labels)
        weighted_sums = [0] * amount_gestures

        for n in range(amount_neighbours):

            # If distance is 0, assign a BIG score. 
            distance = (1 / distances[n][1]) if distances[n][1] != 0. else 10000.
            label = distances[n][0]

            weighted_sums[all_labels.index(label)] += distance

        predicted_label = None
        best_score = 0

        for w in range(amount_gestures):
            if weighted_sums[w] > best_score:
                best_score = weighted_sums[w]
                assigned_label = w

        index = None
        print "\n\n\n\n\nLABEL IS: " + str(assigned_label) + "\n\n"
        for i, mylabel in enumerate(all_labels):
            if mylabel == assigned_label:
                index = i
        assert index != None
        socketIO.emit('classified_gesture', { 'id': all_uuids[index] })
    # Reset the gesture list.
    current_gesture = []

    #print "\n\n\n\nRECORDED\n\n\n\n"

#======================================================

def save_data():
    """ This method is called once when the main loop
    has finished.

    This is the place to save the data.

    """
    global all_gestures
    global all_labels

    print "\n\n\n\nWRITE DATA TO FILE"
    np_gestures = np.array(all_gestures, dtype=object)
    np_labels = np.array(all_labels)
    np_uuids = np.array(all_uuids)
    np_times = np.array(all_times)

    np.save('features', np_gestures)
    np.save('labels', np_labels)
    np.save('uuids', np_uuids)
    np.save('times', np_times)

    assertion_test = np.load('features.npy')

    assert np.array_equal(np_gestures, assertion_test)

    print "Goodbye!"

#======================================================

def short_red_button_press(self):
    """ short red"""
    global current_label
    global all_labels
    print "short red"
    if current_label in all_labels:
        led.clear_display()
        led.draw_text2(0,0,'label' + str(current_label + 1), 2)
        led.display()
        print "Incremented", (current_label + 1)
        current_label += 1


#======================================================

def long_red_button_press(self):
    """ """
    #global state_management
    print "long red"
    #state_management.state = "Shutdown"
    global record_mode
    record_mode = not record_mode

    string_red = 'Record' if record_mode else ('Classify' + str(current_label))
    led.clear_display()
    led.draw_text2(0,0,string_red,2)
    led.display()
    if record_mode is False:
        generate_model()

#======================================================

def short_black_button_press(self):
    """ short black"""
    #print "short black"
    #global current_label
    #global all_labels
    #if current_label in all_labels:
    #    print "Incremented", (current_label + 1)
    #    current_label = current_label + 1

  


    
#======================================================

def long_black_button_press(self):
    """ long black"""
    #print "long black"
    #global record_mode
    #record_mode = not record_mode
    #if record_mode == False:
    #    generate_model()

 
    
#======================================================

def main():

    # Show the user the program has started up
 
    text = 'BrightSign'
    led.draw_text2(0,0,text,2)
    led.display()

    # Provide the appropriate callbacks to the state
    # object so it calls them for us.
    state_management.set_idle_callback(idle)
    state_management.set_recording_callback(recording)
    state_management.set_save_recording_callback(recorded)
    state_management.set_button_callbacks(short_black_button_press,
                                          long_black_button_press,
                                          short_red_button_press,
                                          long_red_button_press)

    # Loop whilst the shutdown button hasn't been pressed.
    # The fps_timer object controls the timing and the
    # state_management calls the appropriate callbacks
    # based on the glove's movement / buttons pressed.
    while state_management.state != "Shutdown":
        fps_timer.start()
        state_management.update()
        fps_timer.sleep()

    # We are terminating the program so write the recorded
    # data to disk.
    save_data()


if __name__ ==  "__main__":
    main()
