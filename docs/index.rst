.. Adafruit Soundboard Library documentation master file, created by
   sphinx-quickstart on Sat Jul 29 19:55:34 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Adafruit Soundboard Library
===========================

.. toctree::
   :hidden:

   Home <self>

.. include:: ../README.rst
   :start-after: main_intro
   :end-before: end_main_intro


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


.. include:: ../README.rst
   :start-after: begin_import
