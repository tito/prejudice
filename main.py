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
from libs.pictureimporter import PictureImporter
from kivy.uix.gridlayout import GridLayout
from os.path import join, exists, dirname, basename
from kivy.uix.stencilview import StencilView
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.utils import platform
from functools import partial
import os
import json
import shutil


MAX_CHOICES = 5
platform = platform()

class AppPopup(Popup):
    message = StringProperty()

class IndiceSelector(StencilView):

    is_answer = BooleanProperty(False)
    title = StringProperty()
    source = StringProperty()

    def detach(self, *args):
        self.parent.remove_widget(self)

    def animate_open(self):
        h = self.height
        self.height = 0
        Animation(height=h, d=.8, t='out_quart').start(self)

    def animate_close(self):
        anim = Animation(height=0., d=.8, t='out_quart')
        anim.bind(on_complete=self.detach)
        anim.start(self)


class AddQuizz(Screen):
    def abort(self):
        pass

    def add_indice(self):
        indice = IndiceSelector()
        indice.animate_open()
        self.ids.indices.add_widget(indice)

    def show_error(self, message):
        popup = AppPopup(message=message)
        popup.open()

    def add(self):
        title = self.ids.title.text
        description = self.ids.description.text
        main_image = self.ids.main_image.source
        indices = self.ids.indices.children
        answers = self.ids.answers.children
        e = self.show_error

        if not title:
            return e('Le titre est manquant')
        if not description:
            return e('La description est manquante')
        if len(title) < 4:
            return e('Le titre est trop petit')
        if len(description) < 4:
            return e('Le titre est trop petit')
        if not main_image:
            return e('Il manque l\'image mystère')
        if len(indices) < 4:
            return e('Il faut au minimum 4 indices')
        if not any([indice.is_answer for indice in indices]):
            return e('Il n\'y a pas d\'indice réponse')

        l_indices = []
        for indice in indices:
            if not (indice.title or indice.source):
                return e('Un indice manque d\'un titre\nou d\'une image')
            l_indices.append({
                'title': indice.title,
                'source': indice.source,
                'is_answer': indice.is_answer})
        l_answers = []
        for answer in answers:
            if answer.source:
                l_answers.append({'source': answer.source})


        # where quizz are stored ?
        quizz = dict(
            title=title,
            description=description,
            main_image=main_image,
            answers=l_answers,
            indices=l_indices)

        App.get_running_app().save_quizz(quizz)



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

class TouchCounter(Widget):
    count = NumericProperty(MAX_CHOICES)

    def __init__(self, **kwargs):
        super(TouchCounter, self).__init__(**kwargs)
        Clock.schedule_once(self.on_count, 0)

    def on_count(self, *args):
        self.clear_widgets()
        for x in range(self.count):
            t = Touch()
            t.y = self.center_y
            t.x = (self.x + t.width / 2.) + (x + 1) * (self.width - t.width) / float(MAX_CHOICES)
            self.add_widget(t)

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

    def _get_remaining_count(self):
        return MAX_CHOICES - len(self.choices)
    remaining_count = AliasProperty(_get_remaining_count, None,
            bind=('choices', ))

    choices = ListProperty([])

    __events__ = ('on_step_done', )

    def __init__(self, **kwargs):
        super(Step, self).__init__(**kwargs)
        Clock.schedule_interval(self._reduce_timer, 1 / 60.)

    def abort(self):
        Clock.unschedule(self._reduce_timer)

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

    def on_step_done(self, go_next=True):
        self.done = True
        Clock.unschedule(self._reduce_timer)
        if go_next:
            App.get_running_app().do_next_step()

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
        if len(self.choices) > MAX_CHOICES:
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

class EndStep(Step):

    title = StringProperty()
    description = StringProperty()
    answers = ListProperty()

    def on_step_done(self):
        super(EndStep, self).on_step_done(False)
        self.show_answer()

    def show_answer(self):
        if self.answers:
            img = self.answers[0]
        else:
            img = None
        self.answer_desc = AnswerDescription(
            title=self.title,
            description=self.description,
            img=img)
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

class Home(Screen):
    pass


class ListQuizzItem(GridLayout):
    fn = StringProperty()
    source = StringProperty()
    selected = BooleanProperty(False)
    listquizz = ObjectProperty()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.selected:
                self.listquizz.start(self)
            else:
                self.listquizz.unselect()
                self.selected = True
            return True


class ListQuizz(Screen):
    
    def update(self):
        app = App.get_running_app()
        self.ids.listquizz.clear_widgets()
        for quizz in app.iterate_quizz():

            data = app.load_quizz(quizz)
            if not data:
                continue

            q = ListQuizzItem(
                    fn=quizz,
                    listquizz=self,
                    title=data['title'],
                    source=join(dirname(quizz), data['main_image']))

            self.ids.listquizz.add_widget(q)

    def unselect(self):
        for item in self.ids.listquizz.children:
            item.selected = False

    def start(self, item):
        App.get_running_app().start_quizz(item.fn)



class Prejudice(App):

    def build(self):
        self.current_step = None
        self.sm = ScreenManager(transition=SlideTransition(
            direction='left', duration=.4))

        self.sm.add_widget(Home(name='home'))

        return self.sm

    def stop_quizz(self):
        if self.current_step:
            self.current_step.abort()
            self.sm.remove_widget(self.current_step)
            self.current_step = None
        self.sm.current = 'home'

    def list_quizz(self):
        if not hasattr(self, '_listquizz'):
            self._listquizz = ListQuizz(name='list-quizz')
            self.sm.add_widget(self._listquizz)
        self._listquizz.update()
        self.sm.current = 'list-quizz'

    def start_quizz(self, quizz):
        self.current_quizz_fn = quizz
        self.current_quizz = data = self.load_quizz(quizz)
        if not self.current_quizz:
            return

        # create steps
        def t(f):
            return join(dirname(quizz), f)

        self.steps = []

        kwargs = dict(
            title=data['title'],
            description=data['description'],
            answers=[t(x['source']) for x in data['answers']])

        # FIX SELECTION ALGO
        indices = data['indices'][:4]
        step = partial(EndStep,
            baseimg=t(data['main_image']),
            img1=t(indices[0]['source']),
            img2=t(indices[1]['source']),
            img3=t(indices[2]['source']),
            img4=t(indices[3]['source']),
            **kwargs)
        self.steps.append(step)

        self.count = 0
        self.stepindex = -1
        self.userevents = {}
        self.events = {}
        self.events_fn = join(dirname(self.current_quizz_fn), 'result.json')
        if exists(self.events_fn):
            try:
                with open(self.events_fn) as fd:
                    self.events = json.load(fd)
            except:
                pass

        self.stepindex = -1
        self.do_next_step()

    def add_quizz(self):
        self.current_step = AddQuizz(name='add-quizz')
        self.sm.add_widget(self.current_step)
        self.sm.current = 'add-quizz'

    def do_next_step(self):
        self.count += 1
        self.stepindex += 1
        name = 's{}'.format(self.count)
        step = self.steps[self.stepindex](name=name)
        self.current_step = step
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

    def on_pause(self):
        return True

    @property
    def quizz_dir(self):
        return self.user_data_dir

    def save_quizz(self, quizz):
        index = 0
        while True:
            quizz_dir = join(self.quizz_dir, 'quizz-{}'.format(index))
            if not exists(quizz_dir):
                break
            index += 1

        # create the quizz directory
        os.makedirs(quizz_dir)

        # save all the images
        self._copy_quizz_image(quizz_dir, quizz, 'main_image')
        for indice in quizz['indices']:
            if indice['source']:
                self._copy_quizz_image(quizz_dir, indice, 'source')
        for answer in quizz['answers']:
            if answer['source']:
                self._copy_quizz_image(quizz_dir, answer, 'source')

        # save our index
        quizz_fn = join(quizz_dir, 'index.json')
        with open(quizz_fn, 'wb') as fd:
            json.dump(quizz, fd)

        self.stop_quizz()
        self.message('Le quizz à été enregistré !')

    def iterate_quizz(self):
        for quizz_dir in os.listdir(self.quizz_dir):
            index = join(self.quizz_dir, quizz_dir, 'index.json')
            if not exists(index):
                continue
            yield index

    def load_quizz(self, fn):
        try:
            with open(fn) as fd:
                return json.load(fd)
        except:
            pass

    def _copy_quizz_image(self, quizz_dir, data, key):
        index = 0
        while True:
            dest_fn = join(quizz_dir, 'img-{}-{}'.format(index,
                basename(data[key])))
            if not exists(dest_fn):
                break
            index += 1
        shutil.copy(data[key], dest_fn)
        data[key] = basename(dest_fn)


    def message(self, msg):
        AppPopup(message=msg).open()




if __name__ == '__main__':
    Prejudice(kv_directory='data').run()
