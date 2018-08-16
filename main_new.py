#!/usr/bin/python


# !!! NOTE FOR TIRED SELF !!!
# Uncomment lines to return websockets functionality:
# 70, 176, 177, 211, 274

import GlovePi


def main():
    # Show the user the program has started up

    pi = GlovePi.GlovePi()

    text = 'BrightSign'
    #pi.led.draw_text2(0, 0, text, 2)
    #pi.led.display()

    # Provide the appropriate callbacks to the state
    # object so it calls them for us.
    pi.state_management.set_idle_callback(pi.idle)
    pi.state_management.set_recording_callback(pi.recording)
    pi.state_management.set_save_recording_callback(pi.recorded)
    pi.state_management.set_button_callbacks(pi.short_black_button_press,
                                             pi.long_black_button_press,
                                             pi.short_red_button_press,
                                             pi.long_red_button_press)

    # Loop whilst the shutdown button hasn't been pressed.
    # The fps_timer object controls the timing and the
    # state_management calls the appropriate callbacks
    # based on the glove's movement / buttons pressed.
    while pi.state_management.state != "Shutdown":
        pi.fps_timer.start()
        pi.state_management.update()
        pi.fps_timer.sleep()

    # We are terminating the program so write the recorded
    # data to disk.
    pi.save_data()


if __name__ == "__main__":
    main()
