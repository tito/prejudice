from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import StringProperty
from kivy.utils import platform
from kivy.lang import Builder
import os
platform = platform()

class PictureImporterBase(RelativeLayout):

    raw_source = StringProperty()
    source = StringProperty()

    def __init__(self, **kwargs):
        super(PictureImporterBase, self).__init__(**kwargs)
        Clock.schedule_once(self.init, -1)

    def init(self, *args):
        self._display = self.ids.display.__self__
        self._selector = self.ids.selector.__self__
        self.remove_widget(self._display)

    def open_select(self):
        # XXX must be implemented
        pass

    def close_select(self):
        # XXX must be implemented
        pass

    def select(self, filename):
        if not filename:
            return
        filename = filename[0]
        self.raw_source = self.source = filename
        self.remove_widget(self._selector)
        self.add_widget(self._display)
        self._display.source = filename
        self.close_select()

    def clear_selection(self):
        self.source = self.raw_source = ''
        self.remove_widget(self._display)
        self.add_widget(self._selector)


if platform in ('android', 'ios'):

    class PictureImporter(PictureImporterBase):
        pass

else:
    from kivy.garden.filechooserthumbview import FileChooserThumbView
    from kivy.uix.popup import Popup

    class PictureImporter(PictureImporterBase):

        def open_select(self):
            content = FileChooserThumbView(
                    path=os.getcwd(),
                    filters=['*.png', '*.jpg', '*.jpeg'])
            content.bind(on_submit=lambda instance, selection, touch:
                    self.select(selection))
            self._popup = Popup(
                    content=content,
                    title='Importer une image',
                    size_hint=(.9, .9))
            self._popup.open()

        def close_select(self):
            if not self._popup:
                return
            self._popup.dismiss()
            self._popup = None

