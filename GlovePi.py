import logging
import os.path
import time
import uuid

#import gaugette.ssd1306
import numpy as np
import scipy.interpolate as interp
from fastdtw import fastdtw
from socketIO_client import LoggingNamespace, SocketIO

from Utility import Utility
from fps import Fps
from state import State


class GlovePi:
    """

    """

    def __init__(self, default_gesture_size=10, minimum_gesture_size=7,
                 dc_pin_id=16, reset_pin_id=15):
        """GlovePi class constructor

        :param default_gesture_size:
        :type default_gesture_size: int
        :param minimum_gesture_size:
        :type minimum_gesture_size: int
        """
        self.gesture_size = default_gesture_size
        self.min_gesture_size = minimum_gesture_size

        self.current_label = 0
        self.current_gesture = []

        if os.path.isfile("uuids.npy"):
            print "Loaded from file"
            self.all_gestures = np.load('features.npy').tolist()
            self.all_labels = np.load('labels.npy').tolist()
            self.all_uuids = np.load('uuids.npy').tolist()
            self.all_times = np.load('times.npy').tolist()
        else:
            self.all_gestures = []
            self.all_labels = []
            self.all_uuids = []
            self.all_times = []

        #self.led = gaugette.ssd1306.SSD1306(reset_pin=reset_pin_id, 
        #                                    dc_pin=dc_pin_id)
        #self.led.begin()
        #self.led.clear_display()

        # Where the buttons are plugged into the pi.
        self.button_1_pin = 5  # Red.
        self.button_2_pin = 21  # Black.

        # Instantiate the state object.
        self.state_management = State(self.button_1_pin, self.button_2_pin)

        # Instantiate the object controlling our desired fps.
        self.desired_fps = 8
        self.fps_timer = Fps(self.desired_fps)

        # Are we recording or classifying gestures?
        self.record_mode = False

        # Classification stuff.
        self.amount_neighbours = 1

        logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
        logging.basicConfig()

        # Websockets
        self.socketIO = SocketIO('http://brightsigndemo.eu-gb.mybluemix.net',
                                 80, LoggingNamespace)

    def idle(self):
        """ Method called when glove is below threshold
        of movement for recording.

        The self is needed in order to bind this method
        to the private method of State. Perhaps set the
        label of the future recordings here.

        """
        if self.record_mode:
            r = "record mode (CLASS " + str(self.current_label) + ")"
        else:
            r = "classify mode"
        print "idle: " + r

    def recording(self):
        """ This method is called each frame of the loop
        when the glove is above the threshold of moving
        for recording.

        Record the sensor data here.

        """
        data = self.state_management.get_sensor_data()
        print data[0:5]

        # Have we got eight elements?
        # assert len(data[-8:]) == 8
        self.current_gesture.append(data[0:5])
        # print "RECORDING"

    def generate_model(self):
        """ This method is called once when the recording mode
        changes to false and the program is in classification
        mode.

        This is so the model can be reduced to one gesture per
        label to save time in the classification stage.
        """
        new_labels = []
        new_uuids = []
        new_gestures = []
        new_dates = []

        unique_labels = np.unique(self.all_labels)

        for label in unique_labels:
            this_gesture_amount = 0
            empty_gesture = [[0.0 for _ in range(5)] for _ in
                             range(self.gesture_size)]
            this_labels_gesture = np.array(empty_gesture)

            needs_uuid = False
            current_uuid_index = None

            dates = []
            for j, gesture in enumerate(self.all_gestures):
                if self.all_labels[j] == label:
                    this_labels_gesture += np.array(gesture)
                    this_gesture_amount += 1
                    dates.append(self.all_times[j])
                    current_uuid_index = j

                    if j >= len(self.all_uuids):
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
                new_uuids.append(self.all_uuids[current_uuid_index])

        self.all_gestures = new_gestures
        self.all_labels = new_labels
        self.all_times = new_dates
        all_uuids = new_uuids
        assert len(self.all_labels) == len(self.all_times) and len(
            all_uuids) == len(
            self.all_labels) and len(self.all_gestures) == len(
            self.all_labels)
        data_to_send = []
        for i, iduu in enumerate(all_uuids):
            data_to_send.append({"id": iduu, "date": self.all_times[i]})

        self.socketIO.emit('state', data_to_send)
        self.socketIO.wait(seconds=1)

        np_labels = np.asarray(self.all_labels)
        np.savetxt("l.csv", np_labels, delimiter=",")
        np.set_printoptions(threshold=np.inf, linewidth=np.inf)
        with open("g.csv", 'w') as f:
            f.write(
                np.array2string(np.asarray(self.all_gestures), separator=','))

        print len(self.all_labels)
        print self.all_labels

    def recorded(self):
        """Called once gesture recording has finished

        After running, the event loop will then resume in an idle state.

        :return:
        """
        # Are we recording or classifying?
        if self.record_mode:

            warped_gesture = []
            transposed_gesture = [list(i) for i in zip(*self.current_gesture)]

            for i, feature in enumerate(transposed_gesture):
                feature_array = np.array(feature)
                feature_interp = interp.interp1d(np.arange(feature_array.size),
                                                 feature_array)
                feature_warped = feature_interp(
                    np.linspace(0, feature_array.size - 1, self.gesture_size))
                warped_gesture.append(feature_warped.tolist())

                self.current_gesture = [list(i) for i in zip(*warped_gesture)]

            if len(self.current_gesture) > self.min_gesture_size:
                self.all_gestures.append(self.current_gesture)
                self.all_labels.append(self.current_label)
                self.all_times.append(time.time())
            else:
                print "Gesture size too small!"
        elif len(self.all_gestures) > 0 and len(
                self.current_gesture) > self.min_gesture_size:

            # We store tuples of our distances and labels here
            distances = []

            for i in range(len(self.all_gestures)):
                time_series_1 = np.array(self.current_gesture, dtype='float')
                time_series_2 = np.array(self.all_gestures[i], dtype='float')
                print time_series_2.shape
                print time_series_1.shape
                distance, path = fastdtw(time_series_1,
                                         time_series_2,
                                         dist=Utility.euc)
                # Packing the label and distance.
                distance_tuple = (self.all_labels[i], distance)

                distances.append(distance_tuple)

            distances.sort(key=lambda tup: tup[1])
            unique_labels = set(self.all_labels)
            amount_gestures = len(unique_labels)
            weighted_sums = [0] * amount_gestures

            for n in range(self.amount_neighbours):
                # If distance is 0, assign a BIG score.
                distance = (1 / distances[n][1]) if distances[n][
                                                        1] != 0. else 10000.
                label = distances[n][0]

                weighted_sums[self.all_labels.index(label)] += distance

            best_score = 0

            assigned_label = ""

            for w in range(amount_gestures):
                if weighted_sums[w] > best_score:
                    best_score = weighted_sums[w]
                    assigned_label = w

            index = None
            print "\n\n\n\n\nLABEL IS: " + str(assigned_label) + "\n\n"
            for i, mylabel in enumerate(self.all_labels):
                if mylabel == assigned_label:
                    index = i
            assert index is not None
            self.socketIO.emit('classified_gesture',
                               {'id': self.all_uuids[index]})

        # Reset the gesture list.
        self.current_gesture = []

        # print "\n\n\n\nRECORDED\n\n\n\n"

    def save_data(self):
        """Saves glove data to features.npy

        This method is called once when the main loop
        has finished.

        :return:
        """
        print "\n\n\n\nWRITE DATA TO FILE"
        np_gestures = np.array(self.all_gestures, dtype=object)
        np_labels = np.array(self.all_labels)
        np_uuids = np.array(self.all_uuids)
        np_times = np.array(self.all_times)

        np.save('features', np_gestures)
        np.save('labels', np_labels)
        np.save('uuids', np_uuids)
        np.save('times', np_times)

        # Assert that saved data is of the correct form and dimensions
        assert np.array_equal(np_gestures, np.load('features.npy'))

        print "Goodbye!"

    def short_red_button_press(self):
        """Event callback for short press of red button

        :return:
        """
        print "short red"
        if self.current_label in self.all_labels:
            #self.led.clear_display()
            #self.led.draw_text2(0, 0, 'label' + str(self.current_label + 1), 2)
            #self.led.display()
            print "Incremented", (self.current_label + 1)
            self.current_label += 1

    def long_red_button_press(self):
        """Event callback for long press of red button

        :return:
        """
        print "long red"
        # self.state_management.state = "Shutdown"
        record_mode = not self.record_mode

        string_red = 'Record' if record_mode else (
                'Classify' + str(self.current_label))

        #self.led.clear_display()
        #self.led.draw_text2(0, 0, string_red, 2)
        #self.led.display()

        if record_mode is False:
            self.generate_model()

    def short_black_button_press(self):
        """Event callback for short press of black button

        :return:
        """
        # print "short black"
        # if current_label in self.all_labels:
        #    print "Incremented", (current_label + 1)
        #    self.current_label = current_label + 1

    def long_black_button_press(self):
        """Event callback for long press of black button

        :return:
        """
        # print "long black"
        # record_mode = not self.record_mode
        # if not record_mode:
        #     self.generate_model()
