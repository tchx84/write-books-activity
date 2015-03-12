# Copyright 2015 Gonzalo Odiard
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""WriteBooks Activity: A tool to write simple books."""

import os
import time
import logging
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Pango

from sugar3.activity import activity
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import EditToolbar
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.datastore import datastore

from imagecanvas import ImageCanvas
from objectchooser import ImageFileChooser

# TODO: get the real scratch path
SCRATCH_PATH = '/home/olpc/Activities/Scratch.activity'
if not os.path.exists(SCRATCH_PATH):
    # this is only for development
    SCRATCH_PATH = \
        '/home/gonzalo/sugar-devel/scratch/scratchonlinux/trunk/scratch'
SCRATCH_BACKGROUNDS_PATH = SCRATCH_PATH + '/Media/Backgrounds'


class WriteBooksActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

        # we do not have collaboration features
        # make the share option insensitive
        self.max_participants = 1

        toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)

        self._edit_toolbar = EditToolbar()
        edit_toolbar_button = ToolbarButton(
            page=self._edit_toolbar, icon_name='toolbar-edit')
        toolbar_box.toolbar.insert(edit_toolbar_button, 1)

        set_background_button = ToolButton('set-background')
        set_background_button.set_tooltip(_('Set the background'))
        set_background_button.connect('clicked',
                                      self.__set_background_clicked_cb)
        toolbar_box.toolbar.insert(set_background_button, -1)

        insert_picture_button = ToolButton('insert-picture')
        insert_picture_button.set_tooltip(_('Add a picture'))
        toolbar_box.toolbar.insert(insert_picture_button, -1)

        rotate_left_button = ToolButton('object-rotate-left')
        rotate_left_button.set_tooltip(_('Rotate left'))
        toolbar_box.toolbar.insert(rotate_left_button, -1)

        rotate_right_button = ToolButton('object-rotate-right')
        rotate_right_button.set_tooltip(_('Rotate right'))
        toolbar_box.toolbar.insert(rotate_right_button, -1)

        mirror_horizontal_button = ToolButton('mirror-horizontal')
        mirror_horizontal_button.set_tooltip(_('Horizontal mirror'))
        toolbar_box.toolbar.insert(mirror_horizontal_button, -1)

        mirror_vertical_button = ToolButton('mirror-vertical')
        mirror_vertical_button.set_tooltip(_('Vertical mirror'))
        toolbar_box.toolbar.insert(mirror_vertical_button, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show_all()

        self._image_canvas = ImageCanvas()
        self._image_canvas.set_halign(Gtk.Align.CENTER)
        self._image_canvas.set_valign(Gtk.Align.CENTER)
        self._image_canvas.set_vexpand(True)

        self._text_editor = TextEditor()

        self._page_counter_label = Gtk.Label('1/1')
        font_desc = Pango.font_description_from_string('12')
        self._page_counter_label.modify_font(font_desc)
        self._page_counter_label.set_halign(Gtk.Align.END)
        self._page_counter_label.set_valign(Gtk.Align.END)

        self._add_page_btn = Gtk.Button()
        self._add_page_btn.set_image(Icon(pixel_size=style.LARGE_ICON_SIZE,
                                          icon_name='list-add'))
        self._add_page_btn.set_valign(Gtk.Align.START)
        self._add_page_btn.set_margin_top(style.DEFAULT_PADDING)
        self._add_page_btn.set_margin_left(style.DEFAULT_PADDING)

        self._prev_page_btn = Gtk.Button()
        self._prev_page_btn.set_image(Icon(pixel_size=style.LARGE_ICON_SIZE,
                                           icon_name='go-previous'))
        self._prev_page_btn.set_valign(Gtk.Align.CENTER)
        self._prev_page_btn.set_margin_right(style.DEFAULT_PADDING)

        self._next_page_btn = Gtk.Button()
        self._next_page_btn.set_image(Icon(pixel_size=style.LARGE_ICON_SIZE,
                                           icon_name='go-next'))
        self._next_page_btn.set_valign(Gtk.Align.CENTER)
        self._next_page_btn.set_margin_left(style.DEFAULT_PADDING)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(".button {background-color: #c0c0c0;}")
        style_context = self._add_page_btn.get_style_context()
        style_context.add_provider(css_provider,
                                   Gtk.STYLE_PROVIDER_PRIORITY_USER)
        style_context = self._prev_page_btn.get_style_context()
        style_context.add_provider(css_provider,
                                   Gtk.STYLE_PROVIDER_PRIORITY_USER)
        style_context = self._next_page_btn.get_style_context()
        style_context.add_provider(css_provider,
                                   Gtk.STYLE_PROVIDER_PRIORITY_USER)

        background = Gtk.EventBox()

        grid = Gtk.Grid()
        grid.set_halign(Gtk.Align.CENTER)

        grid.attach(self._image_canvas, 1, 0, 1, 3)
        self._text_editor.set_vexpand(False)
        grid.attach(self._text_editor, 1, 3, 1, 1)
        grid.attach(self._page_counter_label, 2, 2, 1, 1)
        grid.attach(self._prev_page_btn, 0, 1, 1, 1)
        grid.attach(self._add_page_btn, 2, 0, 1, 1)
        grid.attach(self._next_page_btn, 2, 1, 1, 1)

        background.add(grid)
        self.set_canvas(background)

        self.show_all()

    def __set_background_clicked_cb(self, button):
        chooser = ImageFileChooser(path=SCRATCH_BACKGROUNDS_PATH,
                                   title=_('Select a background'))
        chooser.connect('response', self.__set_backgroud_chooser_response_cb)
        chooser.show()

    def __set_backgroud_chooser_response_cb(self, chooser, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            jobject = datastore.get(chooser.get_selected_object_id())
            if jobject and jobject.file_path:
                tempfile_name = \
                    os.path.join(self.get_activity_root(),
                                 'instance', 'tmp%i' % time.time())
                os.link(jobject.file_path, tempfile_name)
                self._image_canvas.set_background(tempfile_name)
        chooser.destroy()
        del chooser


class TextEditor(Gtk.TextView):

    def __init__(self):
        Gtk.TextView.__init__(self)

        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_pixels_above_lines(0)
        self.set_margin_left(style.GRID_CELL_SIZE)
        self.set_margin_right(style.GRID_CELL_SIZE)
        self.set_margin_bottom(style.DEFAULT_PADDING)
        self.set_size_request(-1, style.GRID_CELL_SIZE * 1.5)

        font_desc = Pango.font_description_from_string('14')
        self.modify_font(font_desc)
