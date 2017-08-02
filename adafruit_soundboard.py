# The MIT License (MIT)
#
# Copyright (c) 2017 Mike Mabey
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_soundboard`
====================================================

This is a MicroPython library for the Adafruit Sound Boards in UART mode!

This library has been adapted from the library written by Adafruit for Arduino,
available at https://github.com/adafruit/Adafruit_Soundboard_library. I have no
affiliation with Adafruit, and they have not sponsored or approved this library
in any way. As such, please do not contact them for support regarding this
library.

Commands the sound board understands (at least the ones I could discern from
the Arduino library) are as follows:

- ``L``: List files on the board
- ``#``: Play a file by number
- ``P``: Play a file by name
- ``+``: Volume up. Range is 0-204, increments of 2.
- ``-``: Volume down
- ``=``: Pause playback
- ``>``: Un-pause playback
- ``q``: Stop playback
- ``t``: Give current position of playback and total time of track
- ``s``: Current track size and total size

* Author(s): Mike Mabey
"""

from machine import UART, Pin
from sys import platform as BOARD

__author__ = 'Mike Mabey'
__license__ = 'MIT'
__copyright_ = 'Copyright 2017, Mike Mabey'

ESP8266 = 'esp8266'
PYBOARD = 'pyboard'
WIPY = 'wipy'

try:
    # Should be supported by all 3 supported boards
    from utime import sleep_ms
except ImportError:
    _supported = ', '.join([ESP8266, PYBOARD, WIPY])
    raise OSError('Unsupported board. Currently only works with {}.'.format(_supported))

SB_BAUD = 9600  # Baud rate of the sound boards
MIN_VOL = 0
MAX_VOL = 204
MAX_FILES = 25
DEBUG = False


class Soundboard:
    """Control an Adafruit Sound Board via UART.

    The :class:`Soundboard` class handles all communication with the sound
    board via :ref:`UART <upy:machine.UART>`, making it easy to get
    information about the sound files on the sound board and control playback.

    If you need to reset the sound board from your MicroPython code, be
    sure to provide the ``rst_pin`` parameter. The soundboard sometimes gets
    out of UART mode and reverts to the factory default of GPIO trigger
    mode. When this happens, it will appear as if the soundboard has
    stoped working for no apparent reason. This library is designed to
    automatically attempt resetting the board if a command fails, since
    that is a common cause. So, it is a good idea to provide this
    parameter.
    """

    def __init__(self, uart_id, rst_pin=None, vol=None, alt_get_files=False, debug=None, **uart_kwargs):
        """
        :param uart_id: ID for the :ref:`UART <upy:machine.UART>` bus to use.
            Acceptable values vary by board. Check the documentation for your
            board for more info.
        :param rst_pin: Identifier for the pin (on the MicroPython board)
            connected to the ``RST`` pin of the sound board. Valid identifiers
            vary by board.
        :param vol: Initial volume level to set. See :attr:`vol` for more info.
        :type vol: int or float
        :param bool alt_get_files: Uses an alternate method to get the list of
            track file names. See :meth:`use_alt_get_files` method for more
            info.
        :param bool debug: When not None, will set the debug output flag to the
            boolean value of this argument using the :meth:`toggle_debug`
            method.
        :param dict uart_kwargs: Additional values passed to the
            :ref:`UART.init() <upy:machine.UART>` method of the UART bus object.
            Acceptable values here also vary by board. It is not necessary to
            include the baud rate among these keyword values, because it will
            be set to ``SB_BAUD`` before the ``UART.init`` function is called.
        """
        if debug is not None:
            self.toggle_debug(bool(debug))

        self._uart = UART(uart_id, SB_BAUD)
        uart_kwargs['baudrate'] = SB_BAUD
        self._uart.init(**uart_kwargs)
        self._files = None
        self._sizes = None
        self._lengths = None
        self._track = {}

        self._cur_vol = None
        self._cur_track = None
        self._reset_attempted = False

        # Setup reset pin
        if BOARD == PYBOARD:
            self._sb_rst = None if rst_pin is None else Pin(rst_pin, mode=Pin.OPEN_DRAIN, value=1)
        else:
            self._sb_rst = None if rst_pin is None else Pin(rst_pin, mode=Pin.IN)

        self.vol = vol

        if alt_get_files:
            self.use_alt_get_files()

        # Get the track lengths (also retrieves the list of files) TODO
        # print('Getting track lengths. This will take a couple seconds.')
        # self._get_lengths()

    def _flush_uart_input(self):
        """Read any available data from the UART bus until none is left."""
        while self._uart.any():
            self._uart.read()

    def _send_simple(self, cmd, check=None, strip=True):
        """Send the command, optionally do a check on the output.

        :param cmd: Command to send over the UART bus. A newline character will
            be appended to the command before sending it, so it's not necessary
            to include one as part of the command.
        :type cmd: str or bytes
        :param check: Depending on the type of `check`, has three different
            behaviors. When None (default), the return value will be whatever
            the output from the command was. When a str or bytes, the return
            value will be True/False, indicating whether the command output
            starts with the value in `check`. When it otherwise evaluates to
            True, return value will be True/False, indicating the output
            started with the first character in `cmd`.
        :type check: str or bytes or None or bool
        :return: Varies depending on the value of `check`.
        :rtype: bytes or bool
        """
        self._flush_uart_input()
        cmd = cmd.strip()  # Make sure there's not more than one newline
        self._uart.write('{}\n'.format(cmd))
        if len(cmd) > 1:
            # We need to gobble the return when there's more than one character in the command
            self._uart.readline()
        try:
            msg = self._uart.readline()
            if strip:
                msg = msg.strip()
            assert isinstance(msg, bytes)
            printif(msg)
        except (AttributeError, AssertionError):
            if self._reset_attempted:
                # Only try resetting once
                return False  # TODO: Better way to handle failed commands? Too broad?
            printif('Got back None from a command. Attempting to restart the board to put it in UART mode.')
            self._reset_attempted = True
            self.reset()
            return self._send_simple(cmd, check)

        if check is None:
            return msg
        else:
            self._reset_attempted = True  # We already sent a command successfully

        if isinstance(check, str):
            return msg.startswith(check.encode())
        elif isinstance(check, bytes):
            return msg.startswith(check)
        elif check:
            return msg.startswith(cmd[0].encode())

    @property
    def files(self):
        """Return a ``list`` of the files on the sound board.

        :rtype: list
        """
        if self._files is None:
            self._get_files()
        return self._files

    @property
    def sizes(self):
        """Return a ``list`` of the files' sizes on the sound board.

        .. seealso:: :meth:`use_alt_get_files`

        :rtype: list
        """
        if self._sizes is None:
            self._get_files()
        return self._sizes

    def _get_files(self):
        """Ask the board for the files and their sizes, store the results."""
        self._flush_uart_input()

        self._files = []
        self._sizes = []
        self._uart.write('L\n')
        sleep_ms(10)
        i = 0
        while self._uart.any():
            msg = self._uart.readline().strip()
            printif(msg)
            fname, fsize = msg.split(b'\t')
            fname = fname.decode()
            self._files.append(fname)
            self._sizes.append(int(fsize))
            self._track[fname] = i
            i += 1

    def _get_files_alt(self):
        """Play every track, get info from feedback."""
        vol = self.vol
        self.vol = 0
        self._files = []
        self._lengths = []
        self._sizes = []
        for i in range(MAX_FILES):
            self.stop()
            msg = self._send_simple('#{}'.format(i))
            if msg.startswith(b'NoFile'):
                # Playing track i failed, it must not be a valid track number
                break
            play, track_num, fname = msg.split(b'\t')
            self._files.append(fname)
            self._track[fname] = i

            sleep_ms(50)
            sec = self.track_time()
            if sec:
                self._lengths.append(sec[1])
            else:
                self._lengths.append(0)
            size = self.track_size()
            if size:
                self._sizes.append(size[1])
            else:
                self._sizes.append(0)

        self.vol = vol

    @property
    def lengths(self):
        """Return a ``list`` of the track lengths in seconds.

        .. note::

            In my own testing of this method, the board always returns a value
            of zero seconds for the length for every track, no matter if it's a
            WAV or OGG file, short or long track.

        :rtype: list
        """
        if self._lengths is None:
            self._get_lengths()
        return self._lengths

    def _get_lengths(self):
        """Store the length of each track."""
        self._get_files_alt()

    def file_name(self, n):
        """Return the name of track ``n``.

        :param int n: Index of a file on the sound board or ``False`` if the
            track number doesn't exist.
        :return: Filename of track ``n``.
        :rtype: str or bool
        """
        try:
            return self.files[n]
        except IndexError:
            return False

    def track_num(self, file_name):
        """Return the track number of the given file name.

        :param str file_name: File name of the track. Should be one of the
            values from the :attr:`files` property.
        :return: The track number of the file name or ``False`` if not found.
        :rtype: int or bool
        """
        try:
            return self._track[file_name]
        except KeyError:
            return False

    def play(self, track=None):
        """Play a track on the board.

        :param track: The index (``int``) or filename (``str``) of the track to
            play.
        :type track: int or str
        :return: If the command was successful.
        :rtype: bool
        """
        if isinstance(track, int):
            cmd = '#'
            num = track
        elif isinstance(track, str):
            cmd = 'P'
            num = self.track_num(track)
        else:
            raise TypeError('You must specify a track by its number (int) or its name (str)')

        if self._send_simple('{}{}'.format(cmd, track), 'play'):
            self._cur_track = num
            return True
        return False

    def play_now(self, track):
        """Play a track on the board now, stopping current track if necessary.

        :param track: The index (``int``) or filename (``str``) of the track to
            play.
        :type track: int or str
        :return: If the command was successful.
        :rtype: bool
        """
        self.stop()
        if not self.play(track):
            # Playing the specified track failed, so just return False
            return False
        return True

    @property
    def vol(self):
        """Current volume.

        This is implemented as a class property, so you can get and set its
        value directly. When setting a new volume, you can use an ``int`` or a
        ``float`` (assuming your board supports floats). When setting to an
        ``int``, it should be in the range of 0-204. When set to a ``float``,
        the value will be interpreted as a percentage of :obj:`MAX_VOL`.

        :rtype: int
        """
        if self._cur_vol is None:
            self.vol_down()
        return self._cur_vol

    @vol.setter
    def vol(self, new_vol):
        if new_vol is None:
            return
        if isinstance(new_vol, float):
            new_vol = int(new_vol * MAX_VOL)
        if not isinstance(new_vol, int):
            printif('Invalid volume level. Try giving an int.')
            return
        elif new_vol > self.vol:
            self.vol_up(new_vol)
        elif new_vol < self.vol:
            self.vol_down(new_vol)

    def vol_up(self, vol=None):
        """Turn volume up by 2 points, return current volume level [0-204].

        :param int vol: Target volume. When not ``None``, volume will be turned
            up to be greater than or equal to this value.
        :rtype: int
        """
        global DEBUG
        printif('Turning volume up')
        if vol is None:
            self._cur_vol = int(self._send_simple('+'))
            return self._cur_vol
        if vol > MAX_VOL:
            printif('{} is above maximum volume. Setting to {} instead.'.format(vol, MAX_VOL))
            vol = MAX_VOL
        self._cur_vol = MIN_VOL - 1
        db = DEBUG
        DEBUG = False
        while vol > self._cur_vol:
            self._cur_vol = int(self._send_simple('+'))
        DEBUG = db
        return self._cur_vol

    def vol_down(self, vol=None):
        """Turn volume down by 2 points, return current volume level [0-204].

        :param int vol: Target volume. When not ``None``, volume will be turned
            down to be less than or equal to this value.
        :rtype: int
        """
        global DEBUG
        printif('Turning volume down')
        if vol is None:
            self._cur_vol = int(self._send_simple('-'))
            return self._cur_vol
        self._cur_vol = MAX_VOL + 1
        if vol < MIN_VOL:
            printif('{} is below minimum volume. Setting to {} instead.'.format(vol, MIN_VOL))
            vol = MIN_VOL
        db = DEBUG
        DEBUG = False
        while vol < self._cur_vol:
            self._cur_vol = int(self._send_simple('-'))
        DEBUG = db
        return self._cur_vol

    def pause(self):
        """Pause playback, return if the command was successful.

        :rtype: bool
        """
        return self._send_simple('=', True)

    def unpause(self):
        """Continue playback, return if the command was successful.

        :rtype: bool
        """
        return self._send_simple('>', True)

    def stop(self):
        """Stop playback, return if the command was successful.

        :rtype: bool
        """
        return self._send_simple('q', True)

    def track_time(self):
        """Return the current position of playback and total time of track.

        :rtype: tuple
        """
        msg = self._send_simple('t')
        if not msg:
            return -1, -1
        printif(len(msg))
        if len(msg) != 11:
            return False
        current, total = msg.decode('utf-8').split(':')
        return int(current), int(total)

    def track_size(self):
        """Return the remaining size and total size.

        It seems the remaining track size refers to the number of bytes left
        for the soundboard to process before the playing of the track will be
        over.

        :return: Remaining track size and total size
        :rtype: tuple
        """
        msg = self._send_simple('s')
        if not msg:
            return -1, -1
        printif(len(msg))
        if len(msg) != 21:
            return False
        remaining, total = msg.decode('utf-8').split('/')
        return int(remaining), int(total)

    def reset(self):
        """Reset the sound board.

        Soft reset the board by bringing the ``RST`` pin low momentarily (10
        ms). This only has effect if the reset pin has been initialized in the
        constructor.

        Doing a soft reset on the board before doing any other actions can help
        ensure that it has been started in UART control mode, rather than GPIO
        trigger mode.

        .. seealso::

            `Soundboard Pinout <https://learn.adafruit.com/adafruit-audio-fx-sound-board/pinouts#uart-pins>`_
                Documentation on the soundboards' pinouts.


        :return: Whether the reset was successful. If the reset pin was not
            initialized in the constructor, this will always return ``False``.
        :rtype: bool
        """
        if self._sb_rst is None:
            # Don't attempt to restart the board if the reset pin wasn't initialized
            return False

        if BOARD == PYBOARD:
            self._sb_rst(0)
            sleep_ms(10)
            self._sb_rst(1)
        else:
            # Pin should already be in IN mode. This allows us to set the value we want to send, then switch to OUT mode
            # just long enough for the value to take effect, and finally switch back to IN mode.
            # self._sb_rst.value(0)
            self._sb_rst(0)
            self._sb_rst.mode(Pin.OUT)
            sleep_ms(10)
            self._sb_rst.mode(Pin.IN)

        sleep_ms(1000)  # Give the board some time to boot
        msg = self._uart.readline().strip()
        printif(msg)  # Date and name

        msg = self._uart.readline().strip()
        printif('Document what this line is: >{}<'.format(msg))  # ? # TODO

        if not msg.startswith('Adafruit FX Sound Board'):
            return False

        sleep_ms(250)

        msg = self._uart.readline().strip()
        printif(msg)  # FAT type

        msg = self._uart.readline().strip()
        printif(msg)  # Number of files

        # Reset volume level and current track
        self.vol = self._cur_vol
        self._cur_track = None

        return True

    def use_alt_get_files(self, now=False):
        """Get list of track files using an alternate method.

        If the list of files is missing tracks you know are on the soundboard,
        try calling this method. It doesn't depend on the soundboard's internal
        command for returning a list of files. Instead, it plays each of the
        tracks using their track numbers and gets the filename and size from
        the output of the play command.

        :param bool now: When set to ``True``, the alternate method of getting
            the files list will be called immediately. Otherwise, the list of
            files will be populated the next time the :attr:`files` property is
            accessed (lazy loading).
        :rtype: None
        """
        self._get_files = self._get_files_alt
        if now:
            self._get_files()

    @staticmethod
    def toggle_debug(debug=None):
        """Turn on/off :obj:`DEBUG` flag.

        :param debug: If None, the :obj:`DEBUG` flag will be toggled to have the
            value opposite of its current value. Otherwise, :obj:`DEBUG` will be
            set to the boolean value of ``debug``.
        :rtype: None
        """
        global DEBUG
        if debug is None:
            DEBUG = not DEBUG
        else:
            DEBUG = bool(debug)


def printif(*values, **kwargs):
    """Print a message if :obj:`DEBUG` is set to ``True``."""
    print(*values, **kwargs) if DEBUG else None
