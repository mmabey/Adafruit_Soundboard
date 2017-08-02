.. automodule:: soundboard
   :members:

   .. py:data:: SB_BAUD

      The baud rate for the soundboards. This shouldn't ever change, since all
      of the soundboard models use the same value.

      .. seealso::

         `Adafruit Audio FX Sound Board Tutorial <https://learn.adafruit.com/adafruit-audio-fx-sound-board>`_
            Adafruit's tutorial on the soundboards.

   .. py:data:: MIN_VOL
   .. py:data:: MAX_VOL

      Minimum volume is 0, maximum is 204.

   .. py:data:: MAX_FILES

      In the Arduino version of this library, it defines the max number of
      files to be 25.

   .. py:data:: DEBUG

      A flag for turning on/off debug messages.

      .. seealso:: :meth:`Soundboard.toggle_debug`, :func:`printif`
