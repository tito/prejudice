#: -*- coding: utf-8 -*-

from kivy.app import App
from kivy.properties import StringProperty, ListProperty, \
        NumericProperty, ObjectProperty, BooleanProperty, \
        AliasProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from os.path import join, exists
import json


class CropCenterImage(Image):

    # redefine norm_image_size to implement a "crop center" approach
    # XXX move that into kivy.uix.image itself, with a new "allow_crop" property

    def get_norm_image_size(self):
        if not self.texture:
            return self.size
        ratio = self.image_ratio
        w, h = self.size
        tw, th = self.texture.size

        iw = w
        ih = iw / ratio
        if ih < h:
            ih = h
            iw = ih * ratio
        return iw, ih

    norm_image_size = AliasProperty(get_norm_image_size, None, bind=(
        'texture', 'size', 'image_ratio', 'allow_stretch'))


class Touch(Widget):
    touch = ObjectProperty()

class ButtonChoice(Button):
    index = NumericProperty()
    step = ObjectProperty()
    source = StringProperty()
    scale = NumericProperty(.5)
    last_touch = ObjectProperty()

    def on_touch_down(self, touch):
        self.last_touch = touch
        return super(ButtonChoice, self).on_touch_down(touch)

class AnswerDescription(RelativeLayout):
    title = StringProperty()
    description = StringProperty()
    img = StringProperty()

class AnswerDetails(RelativeLayout):
    order_user = ListProperty(['', '', '', ''])
    order_all  = ListProperty(['', '', '', ''])



class Step(Screen):
    sid = StringProperty()
    baseimg = StringProperty()
    img1 = StringProperty()
    img2 = StringProperty()
    img3 = StringProperty()
    img4 = StringProperty()
    rchoice1 = NumericProperty(0)
    rchoice2 = NumericProperty(0)
    rchoice3 = NumericProperty(0)
    rchoice4 = NumericProperty(0)
    scale1 = NumericProperty(.5)
    scale2 = NumericProperty(.5)
    scale3 = NumericProperty(.5)
    scale4 = NumericProperty(.5)
    choice1 = NumericProperty(0)
    choice2 = NumericProperty(0)
    choice3 = NumericProperty(0)
    choice4 = NumericProperty(0)
    choices = ListProperty([])
    timer = NumericProperty(20)
    do_replay = BooleanProperty(False)
    last_index = NumericProperty(0)
    done = BooleanProperty(False)


    choices = ListProperty([])

    __events__ = ('on_step_done', )

    def __init__(self, **kwargs):
        super(Step, self).__init__(**kwargs)
        Clock.schedule_interval(self._reduce_timer, 1 / 60.)

    def _reduce_timer(self, dt):
        self.timer -= 1 / 60.
        if self.timer <= 10 and not self.do_replay:
            self.do_replay = True
        if self.do_replay:
            t = int((10 - self.timer) * 10)
            app = App.get_running_app()
            events = list(app.get_events(self.sid, self.last_index, t))
            for action, index in events:
                name = 'rchoice{}'.format(index)
                acc = 1 if action == 'add' else -1
                setattr(self, name, getattr(self, name) + acc)
            self.last_index = t
            if events:
                self.adjust_scales()
        if self.timer <= 0:
            self.dispatch('on_step_done')

    def on_step_done(self):
        self.done = True
        Clock.unschedule(self._reduce_timer)
        #app = App.get_running_app()
        #app.do_next_step()
        self.show_answer()

    def show_answer(self):
        self.answer_desc = AnswerDescription(
            title='Anneau passe-guide',
            description=(
                'L\'anneau passe-guide était fixé sur le devant du char de '
                'guerre à deux roues. Il servait à maintenir en place les '
                'rênes de l\'attelage, le char étant tiré par deux chevaux.'),
            img=self.img1)
        self.answer_details = AnswerDetails(
            order_user=(self.img1, self.img2, self.img3, self.img4),
            order_all=(self.img3, self.img2, self.img1, self.img4))
        Clock.schedule_once(self.animate_answer, 0)
        self.ids.content.add_widget(self.answer_desc)
        self.ids.content.add_widget(self.answer_details)

    def animate_answer(self, *args):
        height = self.answer_details.height
        self.answer_desc.y = self.height
        self.answer_details.top = 0

        from kivy.metrics import dp
        self.answer_desc.height = self.height - height - dp(48)

        from kivy.animation import Animation
        Animation(y=height,
                t='out_quart').start(self.answer_desc)
        Animation(y=0.,
                t='out_quart').start(self.answer_details)

    def choice(self, index, touch):
        if self.done:
            return

        app = App.get_running_app()
        t = int((20 - self.timer) * 10)
        self.choices.append([touch, index])
        self.add_touch(touch)

        # new
        attr = 'choice{}'.format(index)
        setattr(self, attr, getattr(self, attr) + 1)
        if not self.do_replay:
            app.add_event(self.sid, t, index, touch.pos)

        # prev
        if len(self.choices) > 3:
            last_touch, index = self.choices.pop(0)
            self.remove_touch(last_touch)
            attr = 'choice{}'.format(index)
            setattr(self, attr, getattr(self, attr) - 1)
            if not self.do_replay:
                app.del_event(self.sid, t, index, touch.pos)

        self.adjust_scales()

    def adjust_scales(self):
        # adjust scales
        choices = [self.choice1 + self.rchoice1, self.choice2 + self.rchoice2,
                self.choice3 + self.rchoice3, self.choice4 + self.rchoice4]
        scales = [.5, .5, .5, .5]
        step = .005
        for index in range(4):
            acc = step * choices[index]
            for index2 in range(4):
                if index == index2:
                    scales[index] -= acc
                else:
                    scales[index] += acc

        # apply
        self.scale1, self.scale2, self.scale3, self.scale4 = scales

    def add_touch(self, touch):
        self.ids.content.add_widget(Touch(pos=touch.pos, touch=touch))

    def remove_touch(self, touch):
        for child in self.ids.content.children[:]:
            if not isinstance(child, Touch):
                continue
            if child.touch is touch:
                self.ids.content.remove_widget(child)
                return


class Home(Screen):
    pass


class Prejudice(App):

    def build(self):
        self.sm = ScreenManager(transition=SlideTransition(
            direction='left', duration=.4))
        self.sm.add_widget(Home(name='home'))
        #self.start_quizz()
        return self.sm

    def start_quizz(self):
        from kivy.factory import Factory
        self.steps = [
                #Factory.StartStep, 
                Factory.Step1, Factory.Step2, Factory.Step3End]
        self.count = 0
        self.stepindex = -1
        self.userevents = {}
        self.events = {}
        self.events_fn = join(self.user_data_dir, 'bouchon.json')
        if exists(self.events_fn):
            try:
                with open(self.events_fn) as fd:
                    self.events = json.load(fd)
            except:
                pass

        self.stepindex = -1
        self.do_next_step()

    def do_next_step(self):
        self.count += 1
        self.stepindex += 1
        print self.stepindex
        name = 's{}'.format(self.count)
        step = self.steps[self.stepindex](name=name)
        self.sm.add_widget(step)
        self.sm.current = name

    def add_event(self, step, t, index, pos):
        if step not in self.events:
            self.events[step] = []
        if step not in self.userevents:
            self.userevents[step] = []
        self.events[step].append(('add', t, index, pos))
        self.userevents[step].append(('add', t, index, pos))
        self.update_events()

    def del_event(self, step, t, index, pos):
        if step not in self.events:
            self.events[step] = []
        if step not in self.userevents:
            self.userevents[step] = []
        self.events[step].append(('del', t, index, pos))
        self.userevents[step].append(('del', t, index, pos))

    def update_events(self):
        for step, events in self.events.iteritems():
            sorted(events, key=lambda x: x[1])
        for step, events in self.userevents.iteritems():
            sorted(events, key=lambda x: x[1])
        with open(self.events_fn, 'w') as fd:
            json.dump(self.events, fd)

    def get_events(self, step, start, stop):
        if step not in self.events:
            return
        for action, t, index, pos in self.events[step]:
            if start <= t < stop:
                yield action, index

    def get_user_events(self, step, start, stop):
        if step not in self.userevents:
            return
        for action, t, index, pos in self.events[step]:
            if start <= t < stop:
                yield action, index


if __name__ == '__main__':
    Prejudice(kv_directory='data').run()
