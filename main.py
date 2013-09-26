from kivy.app import App
from kivy.properties import StringProperty, ListProperty, \
        NumericProperty, ObjectProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.button import Button
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.clock import Clock
from os.path import join, exists
import json

Builder.load_string('''

<Touch>
    canvas:
        Color:
            rgba: 0, 1, 1, .7
        Ellipse:
            pos: self.x - dp(10), self.y - dp(10)
            size: dp(20), dp(20)

<ButtonChoice>:
    text: ''
    on_press: self.step.choice(self.index, self.last_touch)
    background_color: (0, 0, 0, 0)

    Image:
        size: root.width * root.scale, root.height * root.scale
        x: root.center_x - self.width / 2.
        y: root.center_y - self.height / 2.
        source: root.source

        canvas.before:
            Color:
                rgb: 1, 1, 1
            Rectangle:
                pos: self.x - dp(10), self.y - dp(10)
                size: self.width + dp(20), self.height + dp(20)

<StartStep@Screen>:
    BoxLayout:
        orientation: 'vertical'
        Label:
            text: 'Ceci n\\'est pas un Quizz'
            font_size: '24sp'

        Label:
            text: 'Toucher l\\'image qui vous inspire le plus'

        AnchorLayout:

            Button:
                text: 'Commencer'
                size_hint: None, None
                size: '200dp', '48dp'
                on_release: app.do_next_step()

<Step>:
    BoxLayout:
        orientation: 'vertical'
        spacing: '10dp'
        padding: '10dp'

        Label:
            size_hint_y: None
            height: '22dp'
            text: str(int(root.timer))
            canvas.before:
                Color:
                    rgb: .5, .5, .5
                Rectangle:
                    pos: self.pos
                    size: self.width * (20 - root.timer) / 20., self.height


        BoxLayout:
            orientation: 'horizontal'
                
            Image:
                source: root.baseimg

            GridLayout:
                cols: 2
                spacing: '10dp'

                ButtonChoice:
                    index: 1
                    step: root
                    source: root.img1
                    scale: root.scale1

                ButtonChoice:
                    index: 2
                    step: root
                    source: root.img2
                    scale: root.scale2

                ButtonChoice:
                    index: 3
                    step: root
                    source: root.img3
                    scale: root.scale3

                ButtonChoice:
                    index: 4
                    step: root
                    source: root.img4
                    scale: root.scale4

<Step1@Step>:
    sid: '1'
    baseimg: 'bouchon/bouchon.jpg'
    img1: 'bouchon/picto1_chemise.png'
    img2: 'bouchon/picto1_lac.png'
    img3: 'bouchon/picto1_pocket.png'
    img4: 'bouchon/picto1_voiture.png'

<Step2@Step>:
    sid: '2'
    baseimg: 'bouchon/bouchon.jpg'
    img1: 'bouchon/picto2_fish.png'
    img2: 'bouchon/picto2_leviervitesse.png'
    img3: 'bouchon/picto2_trombonne.png'
    img4: 'bouchon/picto2_zipper.png'

<Step3End@Screen>:
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            orientation: 'horizontal'
            BoxLayout:
                orientation: 'vertical'
                Image:
                    source: 'bouchon/answer.png'
                Label:
                    size_hint_y: None
                    height: '48dp'
                    text: 'Cet objet est un tire-bouton'

            Image:
                source: 'bouchon/dataviz.jpg'

        AnchorLayout:
            size_hint_y: .1
            Button:
                text: 'Recommencer'
                size_hint: None, None
                size: '200dp', '48dp'
                on_release: app.restart()


''')

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
        Clock.unschedule(self._reduce_timer)
        app = App.get_running_app()
        app.do_next_step()

    def choice(self, index, touch):
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
        self.add_widget(Touch(pos=touch.pos, touch=touch))

    def remove_touch(self, touch):
        for child in self.children[:]:
            if not isinstance(child, Touch):
                continue
            if child.touch is touch:
                self.remove_widget(child)
                return


class Prejudice(App):

    def build(self):
        self.steps = [Factory.StartStep, Factory.Step1, Factory.Step2, Factory.Step3End]
        self.count = 0
        self.stepindex = -1
        self.sm = ScreenManager(transition=SlideTransition(
            direction='down', duration=.4))
        self.restart()
        return self.sm

    def restart(self):
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
    Prejudice().run()
