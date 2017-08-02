Adafruit Soundboard Library
===========================

|ports| |docs| |ci| |license_type|

The `Adafruit Soundboards <https://learn.adafruit.com/adafruit-audio-fx-sound-board>`_ are an easy way to add sound to
your maker project, but the `library <https://github.com/adafruit/Adafruit_Soundboard_library>`_ provided by Adafruit
only supports Arduino.

If you've wanted to use one of these boards with a `MicroPython <http://micropython.org/>`_ or `CircuitPython
<https://github.com/adafruit/circuitpython>`_ microcontroller (MCU), this is the library you've been looking for.


Installation
------------

This driver depends on either `MicroPython <http://micropython.org/>`_ or `CircuitPython
<https://github.com/adafruit/circuitpython>`_ and is intended for use to control one of the `Adafruit Audio FX
<https://www.adafruit.com/?q=Adafruit%20Audio%20FX&>`_ boards via UART.

Make sure to get the latest version of the code from `GitHub`_.

CircuitPython Instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^

First, you'll need to get `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_. Then, please ensure
all dependencies are available on the CircuitPython filesystem. This is easily achieved by downloading
`the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

MicroPython Instructions
^^^^^^^^^^^^^^^^^^^^^^^^

At this time, you have to install the driver by copying the |soundboard|_ to your MicroPython board along
with your ``main.py`` file. At some point in the future it may be possible to ``pip install`` it.

.. |soundboard| replace:: ``soundboard.py`` script
.. _soundboard: https://github.com/mmabey/Adafruit_Soundboard/blob/master/src/soundboard.py


Quick Start
-----------

First, you'll need to decide which UART bus you want to use. To do this, you'll need to consult the documentation for
your particular MCU. In these examples, I'm using the original ``pyboard`` (see documentation `here
<http://docs.micropython.org/en/latest/pyboard/>`_) and I'm using UART bus 1 or ``XB``, which uses pin ``X9`` for
transmitting and ping ``X10`` for receiving.

Then, create an instance of the :class:`~soundboard.Soundboard` class, like this:

::

    sound = Soundboard('XB')

I *highly* recommend you also attach the ``RST`` pin on the soundboard to one of the other GPIO pins on the MCU (pin
``X11`` in the example). Also, my alternative method of getting the list of files from the board is more stable (in my
own testing) than the method built-in to the soundboard. Also, I like getting the debug output and I turn the volume
down to 50% while I'm coding. Doing all this looks like the following:

::

    SB_RST = 'X11'
    sound = Soundboard('XB', rst_pin=SB_RST, vol=0.5, debug=True, alt_get_files=True)

Once you've set up all of this, you're ready to play some tracks:

::

    # Play track 0
    sound.play(0)

    # Stop playback
    sound.stop()

    # Play the test file that comes with the soundboard
    sound.play('T00     OGG')

    # Play track 1 immediately, stopping any currently playing tracks
    sound.play_now(1)

    # Pause and resume
    sound.pause()
    sound.unpause()

You can also control the volume in several different ways:

::

    # Raise volume by 2 points (0 min volume, 204 max volume)
    sound.vol_up()

    # Turn down volume until lower than 125
    sound.vol_down(125)

    # Get the current volume
    sound.vol

    # Set volume to 56 (out of 204 maximum)
    sound.vol = 56

    # Set volume to 75% of maximum volume
    sound.vol = 0.75


API Reference
-------------

.. toctree::
    :maxdepth: 2

    api


Contributing
------------

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_soundboard/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.


License
-------

This project is licensed under the `MIT License <https://github.com/mmabey/Adafruit_Soundboard/blob/master/LICENSE>`_.


.. |ports| image:: https://img.shields.io/badge/MicroPython%20Ports-pyboard,%20wipy,%20esp8266-lightgrey.svg
    :alt: Supported ports: pyboard, wipy, esp8266
    :target: `GitHub`_

.. |docs| image:: https://readthedocs.org/projects/adafruit-soundboard/badge/
    :alt: Documentation Status
    :target: `Read the Docs`_

.. |ci| image:: https://travis-ci.org/mmabey/Adafruit_Soundboard.svg
    :alt: CI Build Status
    :target: https://travis-ci.org/mmabey/Adafruit_Soundboard

.. |license_type| image:: https://img.shields.io/github/license/mmabey/Adafruit_Soundboard.svg
    :alt: License: MIT
    :target: `GitHub`_

.. _GitHub: https://github.com/mmabey/Adafruit_Soundboard

.. _Read the Docs: http://adafruit-soundboard.readthedocs.io/
