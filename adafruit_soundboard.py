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
A CircuitPython library for the Adafruit Sound Boards in UART mode!

This library has been adapted from the library written by Adafruit for Arduino,
available at https://github.com/adafruit/Adafruit_Soundboard_library.

* Author(s): Mike Mabey
"""

import board
from busio import UART
from digitalio import DigitalInOut as Dio, DriveMode
from time import sleep

__author__ = 'Mike Mabey'
__license__ = 'MIT'
__copyright_ = 'Copyright 2017, Mike Mabey'

MIN_VOL = 0  #: Minimum volume level.
MAX_VOL = 204  #: Maximum volume level.

#: The baud rate for the sound boards. This shouldn't ever change, since all
#: of the sound board models use the same value.
#:
#: .. seealso::
#:
#:    `Adafruit Audio FX Sound Board Tutorial <https://learn.adafruit.com/adafruit-audio-fx-sound-board>`_
#:    Adafruit's tutorial on the sound boards.
SB_BAUD = 9600

#: A flag for turning on/off debug messages.
#:
#: .. seealso:: :meth:`Soundboard.toggle_debug`, :func:`printif`
DEBUG = False

#: Seconds to delay after sending a command.
CMD_DELAY = 0.010

#: Default UART command timeout in milliseconds. This differs from the default
#: timeout in the |UART|_ class, which is 1000 (1 second). Setting a low
#: timeout greatly improves the performance in the absence of an ``any()``
#: method in |UART|_.
UART_TIMEOUT = 30


class Soundboard:
    """Control an Adafruit Sound Board via UART.

    The :class:`Soundboard` class handles all communication with the sound
    board via `UART`_, making it easy to get information about the sound files
    on the sound board and control playback.

    .. |UART| replace:: ``UART``
    .. _UART: https://circuitpython.readthedocs.io/en/latest/shared-bindings/busio/UART.html

    If you need to reset the sound board from your CircuitPython code, be
    sure to provide the ``rst_pin`` parameter. The sound board sometimes gets
    out of UART mode and reverts to the factory default of GPIO trigger
    mode. When this happens, it will appear as if the sound board has
    stoped working for no apparent reason. This library is designed to
    automatically attempt resetting the board if a command fails, since
    that is a common cause. So, it is a good idea to provide this
    parameter.
    """

    def __init__(self, uart_tx, uart_rx, rst_pin=None, *, vol=None, orig_get_files=False, debug=None,
                 timeout=UART_TIMEOUT, **uart_kwargs):
        """
        :param str uart_tx: Pin name to use for the transmission (``tx``) pin
            for the |UART|_ bus to use, (e.g. ``'D1'``). Acceptable values vary
            by board. Check your board's documentation for more info.
        :param str uart_rx: Pin name to use for the reception (``rx``) pin
            for the |UART|_ bus to use, (e.g. ``'D0'``). Acceptable values vary
            by board. Check your board's documentation for more info.
        :param str rst_pin: Identifier for the pin (on the CircuitPython board)
            connected to the ``RST`` pin of the sound board. Valid identifiers
            vary by board, but should be something like ``'D5'``.
        :param vol: Initial volume level to set. See :attr:`vol` for more info.
        :type vol: int or float
        :param bool orig_get_files: Uses the original method to get the list of
            track file names. See :meth:`use_alt_get_files` method for more
            info.
        :param bool debug: When not None, will set the debug output flag to the
            boolean value of this argument using the :meth:`toggle_debug`
            method.
        :param int timeout: Timeout parameter passed to the |UART|_ object,
            which is in milliseconds. Should be an :class:`int` no greater than
            1000. If not an `int`, will fall back to the default value specified
            in this method's signature, :data:`UART_TIMEOUT`. If an `int` but
            not in the range [1, 1000], will fall back to the |UART|_ class's
            default of 1000.
        :param dict uart_kwargs: Additional values passed to the constructor of
            the |UART|_ object. Acceptable values here also vary by board. It
            is not necessary to include the baud rate among these keyword
            values, because it will be set to :data:`SB_BAUD` when the |UART|_
            object is instantiated.
        """
        if debug is not None:
            self.toggle_debug(bool(debug))

        if not isinstance(timeout, int):
            timeout = UART_TIMEOUT
        elif timeout > 1000 or timeout < 1:
            timeout = 1000

        uart_kwargs['baudrate'] = SB_BAUD
        uart_kwargs['timeout'] = timeout
        self._uart = UART(tx=getattr(board, uart_tx), rx=getattr(board, uart_rx), **uart_kwargs)
        self._files = None
        self._sizes = None
        self._lengths = None
        self._track = {}

        self._cur_vol = None
        self._cur_track = None
        self._reset_attempted = False

        # Setup reset pin
        self._sb_rst = None
        if rst_pin in dir(board):
            # Defaults to IN with no pull
            self._sb_rst = Dio(getattr(board, rst_pin))
            self._sb_rst.switch_to_output(value=1, drive_mode=DriveMode.OPEN_DRAIN)

        self.vol = vol

        if not orig_get_files:
            self.use_alt_get_files()

    def _flush_uart_input(self):
        """Read any available data from the UART bus until none is left."""
        m = self._uart.read()
        while m is not None:
            m = self._uart.read()

    def _send_simple(self, cmd, check=None, strip=True):
        """Send the command, optionally do a check on the output.

        The sound board understands the following commands:

        - ``L``: List files on the board
        - ``#``: Play a file by number
        - ``P``: Play a file by name
        - ``+``: Volume up (range is 0-204, increments of 2)
        - ``-``: Volume down
        - ``=``: Pause playback
        - ``>``: Un-pause playback
        - ``q``: Stop playback
        - ``t``: Give current position of playback and total time of track
        - ``s``: Current track size and total size

        :param bytes cmd: Command to send over the UART bus. A newline character
            will be appended to the command before sending it, so it's not
            necessary to include one as part of the command.
        :param check: Depending on the type of ``check``, has three different
            behaviors. When `None` (default), the return value will be whatever
            the output from the command was. When a `str` or `bytes`, the return
            value will be `True`/`False`, indicating whether the command output
            starts with the value in ``check``. When it otherwise evaluates to
            `True`, return value will be `True`/`False`, indicating the output
            started with the first character in ``cmd``.
        :type check: str or bytes or None or bool
        :return: Varies depending on the value of ``check``.
        :rtype: bytes or bool
        """
        self._flush_uart_input()
        cmd = cmd.strip()  # Make sure there's not more than one newline
        printif('Sending command: {}'.format(cmd))
        self._uart.write(cmd + b'\n')
        sleep(CMD_DELAY)
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

        if isinstance(check, bytes):
            return msg.startswith(check)
        elif check:
            return msg.startswith(cmd[:1])

    @property
    def files(self):
        """Return a :class:`list` of the files on the sound board.

        .. warning::

           The filenames are *always* of type :class:`bytes`, not :class:`str`.

        :rtype: list(bytes)
        """
        if self._files is None:
            self._get_files()
        return self._files

    @files.deleter
    def files(self):
        self._files = None

    @property
    def sizes(self):
        """Return a :class:`list` of the files' sizes on the sound board.

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
        self._uart.write(b'L\n')
        sleep(CMD_DELAY)
        i = 0
        msg = self._uart.readline()
        while msg is not None:
            msg = msg.strip()
            printif(msg)
            fname, fsize = msg.split(b'\t')
            self._files.append(fname)
            self._sizes.append(int(fsize))
            self._track[fname] = i
            i += 1
            msg = self._uart.readline()

    def _get_files_alt(self):
        """Play every track, get info from feedback."""
        vol = self.vol
        self._files = []
        self._lengths = []
        self._sizes = []
        i = 0
        while True:
            self.stop()
            self.vol = 0
            msg = self._send_simple(b'#' + int_to_bytes(i))
            if msg[:6] == b'NoFile':
                # Playing track i failed, it must not be a valid track number
                break
            play, track_num, fname = msg.split(b'\t')
            self._files.append(fname)
            self._track[fname] = i

            sleep(0.050)
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
            i += 1

        self.vol = vol

    @property
    def lengths(self):
        """Return a :class:`list` of the track lengths in seconds.

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

        :param int n: Index of a file on the sound board or `False` if the
            track number doesn't exist.
        :return: Filename of track ``n``.
        :rtype: bytes or bool
        """
        try:
            return self.files[n]
        except IndexError:
            return False

    def track_num(self, file_name):
        """Return the track number of the given file name.

        :param bytes file_name: File name of the track. Should be one of the
            values from the :attr:`files` property.
        :return: The track number of the file name or `False` if not found.
        :rtype: int or bool
        """
        try:
            return self._track[file_name]
        except KeyError:
            return False

    def play(self, track):
        """Play a track on the board.

        :param track: The index (:class:`int`) or filename (:class:`bytes`) of
            the track to play.
        :type track: int or bytes
        :return: If the command was successful.
        :rtype: bool
        """
        if isinstance(track, int):
            cmd = b'#' + int_to_bytes(track)
            num = track
        elif isinstance(track, bytes):
            cmd = b'P' + track
            num = self.track_num(track)
        else:
            raise TypeError('You must specify a track by its number (int) or its name (bytes)')

        if self._send_simple(cmd, b'play'):
            self._cur_track = num
            return True
        return False

    def play_now(self, track):
        """Play a track on the board now, stopping current track if necessary.

        :param track: The index (:class:`int`) or filename (:class:`bytes`) of
            the track to play.
        :type track: int or bytes
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
        value directly. When setting a new volume, you can use an `int` or a
        `float` (assuming your board supports floats). When setting to an
        `int`, it should be in the range of 0-204. When set to a `float`,
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

        :param int vol: Target volume. When not `None`, volume will be turned
            up to be greater than or equal to this value.
        :rtype: int
        """
        global DEBUG
        printif('Turning volume up')
        if vol is None:
            self._cur_vol = int(self._send_simple(b'+'))
            return self._cur_vol
        if vol > MAX_VOL:
            printif('{} is above maximum volume. Setting to {} instead.'.format(vol, MAX_VOL))
            vol = MAX_VOL
        self._cur_vol = MIN_VOL - 1
        db = DEBUG
        DEBUG = False  # Temporarily turn off debug messages
        try:
            while vol > self._cur_vol:
                self._cur_vol = int(self._send_simple(b'+'))
        except Exception:
            DEBUG = db
            raise
        DEBUG = db
        return self._cur_vol

    def vol_down(self, vol=None):
        """Turn volume down by 2 points, return current volume level [0-204].

        :param int vol: Target volume. When not `None`, volume will be turned
            down to be less than or equal to this value.
        :rtype: int
        """
        global DEBUG
        printif('Turning volume down')
        if vol is None:
            self._cur_vol = int(self._send_simple(b'-'))
            return self._cur_vol
        self._cur_vol = MAX_VOL + 1
        if vol < MIN_VOL:
            printif('{} is below minimum volume. Setting to {} instead.'.format(vol, MIN_VOL))
            vol = MIN_VOL
        db = DEBUG
        DEBUG = False  # Temporarily turn off debug messages
        try:
            while vol < self._cur_vol:
                self._cur_vol = int(self._send_simple(b'-'))
        except Exception:
            DEBUG = db
            raise
        DEBUG = db
        return self._cur_vol

    def pause(self):
        """Pause playback, return if the command was successful.

        :rtype: bool
        """
        return self._send_simple(b'=', True)

    def unpause(self):
        """Continue playback, return if the command was successful.

        :rtype: bool
        """
        return self._send_simple(b'>', True)

    def stop(self):
        """Stop playback, return if the command was successful.

        :rtype: bool
        """
        if not self._send_simple(b'q', True):
            return False
        self._uart.readline()  # Should be "done\r\r\n"

    def track_time(self):
        """Return the current position of playback and total time of track.

        :rtype: tuple
        """
        msg = self._send_simple(b't')
        if not msg:
            return -1, -1
        printif(len(msg))
        if len(msg) != 11:
            return False
        current, total = msg.split(b':')
        return int(current), int(total)

    def track_size(self):
        """Return the remaining size and total size.

        It seems the remaining track size refers to the number of bytes left
        for the sound board to process before the playing of the track will be
        over.

        :return: Remaining track size and total size
        :rtype: tuple
        """
        msg = self._send_simple(b's')
        if not msg:
            return -1, -1
        printif(len(msg))
        if len(msg) != 21:
            return False
        remaining, total = msg.split(b'/')
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
                Documentation on the sound boards' pinouts.


        :return: Whether the reset was successful. If the reset pin was not
            initialized in the constructor, this will always return ``False``.
        :rtype: bool
        """
        if self._sb_rst is None:
            # Don't attempt to restart the board if the reset pin wasn't initialized
            return False

        self._sb_rst.value = 0
        sleep(CMD_DELAY)
        self._sb_rst.value = 1

        sleep(1)  # Give the board some time to boot
        msg = self._uart.readline().strip()
        printif(msg)  # Blank line

        msg = self._uart.readline().strip()
        printif(msg)  # Date and name

        if not msg[:23] == b'Adafruit FX Sound Board':
            return False

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

        If the list of files is missing tracks you know are on the sound board,
        try calling this method. It doesn't depend on the sound board's internal
        command for returning a list of files. Instead, it plays each of the
        tracks using their track numbers and gets the filename and size from
        the output of the play command.

        :param bool now: When set to `True`, the alternate method of getting
            the files list will be called immediately. Otherwise, the list of
            files will be populated the next time the :attr:`files` property is
            accessed (lazy loading).
        :rtype: None
        """
        self._get_files = self._get_files_alt
        del self.files
        if now:
            self._get_files()

    @staticmethod
    def toggle_debug(debug=None):
        """Turn on/off :obj:`DEBUG` flag.

        :param debug: If `None`, the :obj:`DEBUG` flag will be toggled to have
            the value opposite of its current value. Otherwise, :obj:`DEBUG`
            will be set to the boolean value of ``debug``.
        :rtype: None
        """
        global DEBUG
        if debug is None:
            DEBUG = not DEBUG
        else:
            DEBUG = bool(debug)


def printif(*values, **kwargs):
    """Print a message if :obj:`DEBUG` is set to `True`."""
    print(*values, **kwargs) if DEBUG else None


def int_to_bytes(num):
    """Convert the given integer to bytes.

    For example, giving the int ``1`` would return the byte string ``b'1'``.

    :param int num: The number to convert. Should be non-negative, but works
        either way.
    :return: The number as a byte string.
    :rtype: bytes
    """
    if num == 0:
        return b'0'
    nums = [b'0', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9']
    b = b''
    if num < 0:
        sign = b'-'
        num = 0 - num
    else:
        sign = b''
    while num != 0:
        b = nums[num % 10] + b
        num //= 10
    return sign + b
