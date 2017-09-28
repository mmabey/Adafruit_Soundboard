Adafruit Soundboard Library
===========================

|ports| |docs| |version| |ci| |license_type|

.. toctree::
   :maxdepth: 2
   :hidden:

   Home <self>
   api

The `Adafruit Soundboards <https://learn.adafruit.com/adafruit-audio-fx-sound-board>`_ are an easy way to add sound to
your maker project, but the `library <https://github.com/adafruit/Adafruit_Soundboard_library>`_ provided by Adafruit
only supports Arduino.

If you've wanted to use one of these boards with a `MicroPython <http://micropython.org/>`_ or `CircuitPython
<https://github.com/adafruit/circuitpython>`_ microcontroller (MCU), this is the library you've been looking for. Please
note, though, if you're planning to use MicroPython, you should refer to the separate repository
(https://github.com/mmabey/Adafruit_Soundboard_uPy) and documentation (coming soon), as their implementations differ.

Take a look at the latest documentation on `Read the Docs`_ and the latest code on `GitHub`_.


Installation
------------

This driver depends on either `MicroPython <http://micropython.org/>`_ or `CircuitPython
<https://github.com/adafruit/circuitpython>`_ and is intended for use to control one of the `Adafruit Audio FX
<https://www.adafruit.com/?q=Adafruit%20Audio%20FX&>`_ boards via UART.

Make sure to get the latest version of the code from `GitHub`_.

CircuitPython Instructions
^^^^^^^^^^^^^^^^^^^^^^^^^^

First, you'll need to get `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_ and install it on your
board. Then, please ensure all dependencies are available on the CircuitPython filesystem. This is easily achieved by
downloading `the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

Next, you need to know what *version* of CircuitPython you installed on your MCU. The next steps you take depend on if
your version of CircuitPython matches what is listed in the "CircuitPython Version" badge above.

Matching Version
~~~~~~~~~~~~~~~~

If the version *matches* the "CircuitPython Version" badge above, simply download the latest version of the
``adafruit_soundboard.mpy`` script from `the releases page <https://github.com/mmabey/Adafruit_Soundboard/releases>`_
and copy it to the MCU.

Non-Matching Version
~~~~~~~~~~~~~~~~~~~~

If you are using a version of CircuitPython that's *different* from what's listed in the "CircuitPython Version" badge
above, do the following:

1. Clone the CircuitPython repository at the version tag you're using (requires the installation of ``git``):

   ::

      git clone -b <VERSION HERE> https://github.com/adafruit/circuitpython.git

2. Build the ``mpy-cross`` cross-compiler (requires the \*nix program ``make``):

   ::

      which make  # If this command gives no output, you don't have make installed
      cd circuitpython/mpy-cross && make

3. Clone the sound board library:

   ::

      git clone https://github.com/mmabey/Adafruit_Soundboard.git soundboard

4. Cross-compile the library, which will create a file named ``adafruit_soundboard.mpy``:

   ::

      cd soundboard && mpy-cross adafruit_soundboard.py

5. Copy the ``adafruit_soundboard.mpy`` file to your MCU.


MicroPython Instructions
^^^^^^^^^^^^^^^^^^^^^^^^

Please refer to the separate repository (https://github.com/mmabey/Adafruit_Soundboard_uPy) and documentation (coming
soon), for using this library with MicroPython.


Quick Start
-----------

First, you'll need to decide which pins you want to use for the UART bus. To do this, you'll need to consult the
documentation for your particular MCU. In these examples, I'm using the Adafruit `Metro M0 Express
<https://www.adafruit.com/product/3505>`_ and I'm using pin ``D0`` for the UART ``RX`` (receiving) and ``D1`` for ``TX``
(transmitting). See the `pinout guide <http://circuitpython.readthedocs.io/en/2.x/atmel-samd/README.html#pinout>`_ for
information on other supported pins for ``RX`` and ``TX``.

Next, you *have to* connect the ``UG`` pin on the sound board to ``GND`` somehow. This is what tells the sound board to
function in UART mode. For more info, please refer to Adafruit's guide for the sound boards:
https://learn.adafruit.com/adafruit-audio-fx-sound-board/serial-audio-control#general-usage

Then, create an instance of the :class:`~adafruit_soundboard.Soundboard` class, like this:

::

   from adafruit_soundboard import Soundboard
   sound = Soundboard('D1', 'D0')

I *highly* recommend you also attach the ``RST`` pin on the sound board to one of the other GPIO pins on the MCU (pin
``D3`` in the example). Also, I like getting the debug output and I turn the volume down to 50% while I'm coding. Doing
all this looks like the following:

::

    sound = Soundboard('D1', 'D0', 'D3', vol=0.5, debug=True)

Once you've set up all of this, you're ready to play some tracks:

::

    # Play track 0
    sound.play(0)

    # Stop playback
    sound.stop()

    # Play the test file that comes with the sound board
    sound.play(b'T00     OGG')

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

Please read the |api|_ for additional details on how to use the library.

.. |api| replace:: ``adafruit_soundboard`` API reference
.. _api: api.html


Contributing
------------

Contributions are welcome! Please read the `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_soundboard/blob/master/CODE_OF_CONDUCT.md>`_ before contributing to
help this project stay welcoming.


License
-------

This project is licensed under the `MIT License <https://github.com/mmabey/Adafruit_Soundboard/blob/master/LICENSE>`_.


.. |ports| image:: https://img.shields.io/badge/CircuitPython%20Version-2.0-blue.svg
    :alt: Supported version of CircuitPython: 2.0
    :target: `GitHub`_

.. |docs| image:: https://readthedocs.org/projects/adafruit-soundboard/badge/
    :alt: Documentation Status
    :target: `Read the Docs`_

.. |version| image:: https://img.shields.io/github/release/mmabey/Adafruit_Soundboard/all.svg
    :alt: Release Version
    :target: `GitHub Releases`_

.. |ci| image:: https://travis-ci.org/mmabey/Adafruit_Soundboard.svg
    :alt: CI Build Status
    :target: https://travis-ci.org/mmabey/Adafruit_Soundboard

.. |license_type| image:: https://img.shields.io/github/license/mmabey/Adafruit_Soundboard.svg
    :alt: License: MIT
    :target: `GitHub`_

.. _GitHub: https://github.com/mmabey/Adafruit_Soundboard

.. _GitHub Releases: https://github.com/mmabey/Adafruit_Soundboard/releases

.. _Read the Docs: http://adafruit-soundboard.readthedocs.io/
