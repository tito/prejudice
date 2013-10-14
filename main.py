#: -*- coding: utf-8 -*-
'''
A Priori
========

.. author:: Mathieu Virbel <mat@meltingrocks.com>
'''

__version__ = '0.3'

import kivy
kivy.require('1.7.2')

import os
import json
import shutil
import sys
from math import ceil
from random import random
from kivy.app import App
from kivy.metrics import dp
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
from kivy.core.audio import SoundLoader
from os.path import join, exists, dirname, basename
from kivy.uix.stencilview import StencilView
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.utils import platform
from functools import partial

sys.path += ['libs']
app = None


MAX_CHOICES = 5
platform = platform()

class AppPopup(Popup):
    message = StringProperty()

class IndiceSelector(StencilView):

    is_answer = BooleanProperty(False)
    title = StringProperty()
    source = StringProperty()
    step_index = NumericProperty(0)

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

class Separator(Widget):
    pass

class AddQuizzStep(RelativeLayout):
    ctrl = ObjectProperty()
    index = NumericProperty(1)

    def delete(self):
        children = self.ctrl.ids.indices.children
        index = children.index(self)
        for child in children[index-4:index+1]:
            if isinstance(child, IndiceSelector):
                child.animate_close()
            else:
                self.ctrl.ids.indices.remove_widget(child)
        try:
            self.ctrl.ids.indices.remove_widget(children[index])
        except:
            pass

class AddQuizz(Screen):
    step_current_index = NumericProperty(1)
    def abort(self):
        pass

    def on_leave(self):
        app.sm.remove_widget(self)
        print 'removed, and should be destroyed.'

    def add_step(self):
        self.step_current_index += 1
        index = len([x for x in self.ids.indices.children \
                if isinstance(x, AddQuizzStep)]) + 1
        if self.ids.indices.children:
            self.ids.indices.add_widget(Separator())
        self.ids.indices.add_widget(AddQuizzStep(ctrl=self, index=index))
        for x in xrange(4):
            self.add_indice()

    def add_indice(self):
        indice = IndiceSelector(step_index=self.step_current_index)
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
        if len([indice for indice in indices if isinstance(indice, IndiceSelector)]) < 4:
            return e('Il faut au minimum 4 indices / 1 étape')

        l_steps = []
        step = []

        for indice in indices:
            if not isinstance(indice, IndiceSelector):
                continue
            if not (indice.title or indice.source):
                return e('Un indice manque d\'un titre\nou d\'une image')
            step.append({
                'title': indice.title,
                'source': indice.source,
                'is_answer': indice.is_answer})
            if len(step) == 4:
                if not any([x['is_answer'] for x in step]):
                    index = len(l_steps) + 1
                    return e('L\'étape {} n\'a pas d\'indice réponse'.format(
                        index))

                l_steps.append(step)
                step = []


        if step and len(step) == 4:
            l_steps.append(step)

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
            steps=l_steps)

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
    is_other = BooleanProperty(False)

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
    last_touch = ObjectProperty()
    title = StringProperty()

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
    choices = ListProperty([])
    timer = NumericProperty(20)
    do_replay = BooleanProperty(False)
    last_index = NumericProperty(0)
    done = BooleanProperty(False)
    indices = ListProperty()

    choice1 = NumericProperty()
    choice2 = NumericProperty()
    choice3 = NumericProperty()
    choice4 = NumericProperty()

    def _get_remaining_count(self):
        return MAX_CHOICES - len(self.choices)
    remaining_count = AliasProperty(_get_remaining_count, None,
            bind=('choices', ))

    choices = ListProperty([])

    __events__ = ('on_step_done', )

    def __init__(self, **kwargs):
        self.indices = kwargs.pop('indices')
        super(Step, self).__init__(**kwargs)

    def abort(self):
        Clock.unschedule(self._reduce_timer)

    def on_enter(self):
        Clock.schedule_interval(self._reduce_timer, 1 / 60.)
        app.play('TIME_sans_5sec')

    def _reduce_timer(self, dt):
        self.timer -= 1 / 60.
        if self.timer <= 10 and not self.do_replay:
            self.do_replay = True
            app.play('TIME_sans_5sec')
            app.play('5sec')

            self.generate_other_choices()

        if self.timer <= 0:
            self.dispatch('on_step_done')

    def on_step_done(self, go_next=True):
        self.analyse_stats()
        self.done = True
        Clock.unschedule(self._reduce_timer)
        if go_next:
            App.get_running_app().do_next_step()

    def generate_other_choices(self):
        choices = app.get_choices()
        print choices
        m = dp(30)
        for index, choice in enumerate(choices):
            for count in xrange(choice):
                widget = list(reversed(self.ids.choices.children))[index]
                x = random() * (widget.width - m * 2) + widget.x + m
                y = random() * (widget.height - m * 2) + widget.y + m
                touch = Touch(pos=(x, y), is_other=True)
                self.ids.content.add_widget(touch)

    def choice(self, index, touch):
        if self.done:
            return

        self.choices.append([touch, index, self.do_replay])
        self.add_touch(touch)

        # new
        attr = 'choice{}'.format(index)
        setattr(self, attr, getattr(self, attr) + 1)

        # prev
        if len(self.choices) > MAX_CHOICES:
            last_touch, index, _ = self.choices.pop(0)
            self.remove_touch(last_touch)
            attr = 'choice{}'.format(index)
            setattr(self, attr, getattr(self, attr) - 1)

    def add_touch(self, touch):
        self.ids.content.add_widget(Touch(pos=touch.pos, touch=touch))

    def remove_touch(self, touch):
        for child in self.ids.content.children[:]:
            if not isinstance(child, Touch):
                continue
            if child.touch is touch:
                self.ids.content.remove_widget(child)
                return

    def analyse_stats(self):
        for touch, index, influence in self.choices:
            good = self.indices[index - 1]['is_answer']
            app.add_stat(good, influence)
            app.update_choices(index)


class EndStep(Step):

    title = StringProperty()
    description = StringProperty()
    answers = ListProperty()

    def on_step_done(self):
        super(EndStep, self).on_step_done(False)
        app.save_choices()
        self.show_answer()

    def show_answer(self):
        app.play('END')
        if self.answers:
            img = self.answers[0]
        else:
            img = None
        self.answer_desc = AnswerDescription(
            title=self.title,
            description=self.description,
            img=img or '')
        #self.answer_details = AnswerDetails(
        #    order_user=(self.img1, self.img2, self.img3, self.img4),
        #    order_all=(self.img3, self.img2, self.img1, self.img4))
        Clock.schedule_once(self.animate_answer, 0)
        self.ids.content.add_widget(self.answer_desc)
        #self.ids.content.add_widget(self.answer_details)

    def animate_answer(self, *args):
        height = 0
        #height = self.answer_details.height
        self.answer_desc.y = self.height
        #self.answer_details.top = 0

        from kivy.metrics import dp
        self.answer_desc.height = self.height - height - dp(48)

        from kivy.animation import Animation
        Animation(y=height, t='out_quart').start(self.answer_desc)
        #Animation(y=0., t='out_quart').start(self.answer_details)

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
                app.play('CLIC_normal')
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


class LoadingScreen(Screen):
    pass


class StatsScreen(Screen):
    good_count = NumericProperty(0)
    bad_count = NumericProperty(0)
    good_percent = NumericProperty(0)
    bad_percent = NumericProperty(0)
    good_inf_percent = NumericProperty(0)
    bad_inf_percent = NumericProperty(0)
    pattern_good = ObjectProperty()
    pattern_bad = ObjectProperty()

    def __init__(self, **kwargs):
        super(StatsScreen, self).__init__(**kwargs)
        self.pattern_good = Image(source='data/stats-pattern-good.png').texture
        self.pattern_good.wrap = 'repeat'
        self.pattern_bad = Image(source='data/stats-pattern-bad.png').texture
        self.pattern_bad.wrap = 'repeat'

    def on_enter(self):
        self.update()

    def on_pre_enter(self):
        self.good_percent = self.bad_percent = \
            self.good_inf_percent = self.bad_inf_percent = \
            self.good_count = self.bad_count = 0

    def update(self):
        good_count = sum(app.stats['good'])
        bad_count = sum(app.stats['bad'])
        count = good_count + bad_count
        if not count:
            return

        good_percent = good_count / float(count)
        bad_percent = bad_count / float(count)

        good_inf_percent = 0
        if good_count:
            good_inf_percent = app.stats['good'][1] / float(good_count)

        bad_inf_percent = 0
        if bad_count:
            bad_inf_percent = app.stats['bad'][1] / float(bad_count)

        ratio = 1 / max(good_percent, bad_percent)
        good_percent *= ratio
        bad_percent *= ratio

        Animation(good_percent=good_percent, bad_percent=bad_percent,
                good_count=good_count, bad_count=bad_count,
                good_inf_percent=good_inf_percent,
                bad_inf_percent=bad_inf_percent,
                d=1., t='out_quart').start(self)


class Prejudice(App):

    def build(self):
        global app
        app = self
        self.sounds = {}
        self.load_stats()
        self.current_step = None
        self.sm = ScreenManager(transition=SlideTransition(
            direction='left', duration=.4))

        self.sm.add_widget(LoadingScreen(name='loading'))
        self.sm.add_widget(Home(name='home'))

        self.sm.current = 'home'

        app.play('ACCUEIL')
        return self.sm

    def show_stats(self):
        if not hasattr(self, '_statsscr'):
            self._statsscr = StatsScreen(name='stats')
            self.sm.add_widget(self._statsscr)
        self.sm.transition.direction = 'left'
        self.sm.current = 'stats'

    def stop_quizz(self):
        if self.current_step:
            self.current_step.abort()
            self.sm.remove_widget(self.current_step)
            self.current_step = None
        self.sm.transition.direction = 'right'
        self.sm.current = 'home'

    def list_quizz(self):
        if not hasattr(self, '_listquizz'):
            self._listquizz = ListQuizz(name='list-quizz')
            self.sm.add_widget(self._listquizz)
        self._listquizz.update()
        self.sm.transition.direction = 'left'
        self.sm.current = 'list-quizz'

    def start_quizz(self, quizz):
        self.current_quizz_fn = quizz
        self.current_quizz = data = self.load_quizz(quizz)
        if not self.current_quizz:
            return

        self.load_choices()

        # create steps
        def t(f):
            return join(dirname(quizz), f)

        self.steps = []

        kwargs = dict(
            title=data['title'],
            description=data['description'],
            answers=[t(x['source']) for x in data['answers']])

        index_max = len(data['steps']) - 1
        for index, indices in enumerate(data['steps']):
            if not indices:
                continue
            cls = Step if index != index_max else EndStep
            step = partial(cls,
                baseimg=t(data['main_image']),
                indices=indices,
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
        self.sm.add_widget(AddQuizz(name='add-quizz'))
        self.sm.transition.direction = 'left'
        self.sm.current = 'add-quizz'

    def do_next_step(self):
        self.count += 1
        self.stepindex += 1
        name = 's{}'.format(self.count)
        step = self.steps[self.stepindex](name=name)
        self.current_step = step
        self.sm.add_widget(step)
        self.sm.current = name

    '''
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

    '''

    #
    # Quizz management
    #

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
        for indices in quizz['steps']:
            for indice in indices:
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
        shutil.copyfile(data[key], dest_fn)
        data[key] = basename(dest_fn)

    #
    # Utils
    #

    def on_pause(self):
        return True

    def message(self, msg):
        AppPopup(message=msg).open()

    def play(self, name):
        if name not in self.sounds:
            fn = join('data', 'sounds', '{}.wav'.format(name))
            self.sounds[name] = SoundLoader.load(fn)

        sound = self.sounds[name]
        if sound.state == 'play':
            sound.stop()
        sound.play()

    #
    # Statistics management
    #

    @property
    def stats_fn(self):
        return join(self.user_data_dir, 'stats.json')

    def load_stats(self):
        self.stats = { 'good': [0, 0], 'bad': [0, 0] }
        try:
            if exists(self.stats_fn):
                with open(self.stats_fn) as fd:
                    self.stats = json.load(fd)
        except:
            pass

    def save_stats(self):
        with open(self.stats_fn, 'wb') as fd:
            json.dump(self.stats, fd)

    def add_stat(self, good, influence):
        key = 'good' if good else 'bad'
        index = 1 if influence else 0
        self.stats[key][index] += 1
        self.save_stats()


    #
    # Events
    #

    @property
    def choice_fn(self):
        return join(dirname(self.current_quizz_fn), 'choices.json')

    def load_choices(self):
        self.choices = {}
        try:
            if exists(self.choice_fn):
                with open(self.choice_fn) as fd:
                    self.choices = json.load(fd)
        except:
            pass
        print self.choices

    def update_choices(self, index):
        index = str(index)
        if index not in self.choices:
            self.choices[index] = 0
        self.choices[index] += 1

    def save_choices(self):
        with open(self.choice_fn, 'wb') as fd:
            json.dump(self.choices, fd)

    def get_choices(self):
        count = sum(self.choices.values()) / 5.
        if count <= 1:
            return (0, 0, 0, 0)
        return (
            int(ceil(self.choices.get('1', 0) / float(count))),
            int(ceil(self.choices.get('2', 0) / float(count))),
            int(ceil(self.choices.get('3', 0) / float(count))),
            int(ceil(self.choices.get('4', 0) / float(count))))


if __name__ == '__main__':
    Prejudice(kv_directory='data').run()
