from argparse import Namespace
from enum import Enum
import json
import mock
import pytest
import tempfile

import numpy as np

from paranormal.parameter_interface import *
from paranormal.params import *


################################
# Helper Classes and Functions #
################################


class E(Enum):
    X = 0
    Y = 1


class P(Params):
    b = BoolParam(default=True, help='a boolean!')
    i = IntParam(default=1, help='an integer!')
    f = FloatParam(default=0.5, help='A float!')
    r = IntParam(required=True, help='An integer that is required!')
    e = EnumParam(cls=E, help='an enum', default=E.X)
    l = ListParam(subtype=int, default=[0, 1, 2], help='a list')
    a = ArangeParam(help='arange param', default=[0, 100, 5])


class Colors(Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    YELLOW = 3


class MySummer(Params):
    dpw_s = LinspaceParam(help='Drinks per weekend', expand=True, default=[0, None, 15],
                          prefix='s_')
    c = EnumParam(cls=Colors, default=Colors.BLUE, help='Color of the sky')
    t = FloatParam(help='Time spent sunbathing before I burn', default=60, unit='ns')
    f = FloatParam(help='Frequency of birds chirping', unit='MHz', default=None)
    do_something_crazy = BoolParam(default=False, help='Do something crazy')


class MyWinter(Params):
    s = FloatParam(default=12, help='hours sleeping per 24 hrs')
    hib = BoolParam(default=False, help='Whether or not to hibernate')
    dpw_w = LinspaceParam(help='Drinks per weekend', expand=True, default=[0, None, 15],
                          prefix='w_')


class MySpring(Params):
    flowers = FloatParam(default=12, help='flowers sprouting per day')
    dpw_s = LinspaceParam(help='Drinks per weekend', expand=True, default=[0, None, 15],
                          prefix='sp_')


class PositionalsA(Params):
    x = FloatParam(positional=True, help='a positional float')
    y = StringParam(positional=True, help='a positional string')
    z = LinspaceParam(positional=True, help='a positional linspace')


class PositionalsB(Params):
    a = IntParam(positional=True, help='a positional int')
    b = IntParam(help='an int')


class FreqSweep(Params):
    freqs = LinspaceParam(help='freqs', expand=True, default=[10, 20, 30], unit='MHz',
                          prefix='f_')
    times = LinspaceParam(help='times', expand=True, default=[100, 200, 50], unit='us',
                          prefix='t_')


class TimeSweep(Params):
    times = LinspaceParam(help='times', expand=True, default=[100, 500, 20], unit='ns',
                          prefix='t_')


class DoubleSweep(Params):
    freq_sweep = FreqSweep()
    time_sweep = TimeSweep()


def _compare_two_param_item_lists(a, b):
    for (k, v), (k_cor, v_cor) in zip(a, b):
        assert k == k_cor
        if isinstance(v, np.ndarray):
            assert np.allclose(v, v_cor)
        else:
            assert v == v_cor


#####################
# Actual Unit Tests #
#####################


def test_params():

    p = P(b=False, i=2, f=0.2, r=5)
    correct_values = [('b', False), ('i', 2), ('f', 0.2), ('r', 5), ('e', E.X), ('l', [0, 1, 2]),
                      ('a', np.array([0,  5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70,
                                      75, 80, 85, 90, 95]))]
    _compare_two_param_item_lists(p.items(), correct_values)

    # test with an argument that isn't in P
    with pytest.raises(KeyError):
        P(x=5, r=2)

    # Try without providing r
    with pytest.raises(KeyError):
        P()


def test_json_serialization():

    # to_json
    p = P(r=5)
    s = json.dumps(to_json_serializable_dict(p, include_defaults=False))
    assert s == '{"r": 5, "_type": "P", "_module": "test_parameter_interface"}'

    s = json.dumps(to_json_serializable_dict(p, include_defaults=True))
    assert s == '{"b": true, "i": 1, "f": 0.5, "r": 5, "e": "X", "l": [0, 1, 2], ' \
                '"a": [0, 100, 5], "_type": "P", "_module": "test_parameter_interface"}'
    # from json
    p = P(r=3)
    j = json.loads(json.dumps(to_json_serializable_dict(p, include_defaults=True)))
    assert p == from_json_serializable_dict(j)

    j = json.loads(json.dumps(to_json_serializable_dict(p, include_defaults=False)))
    assert p == from_json_serializable_dict(j)


def test_yaml_serialization():
    p = P(r=10)
    temp = tempfile.NamedTemporaryFile(delete=False, mode='w+t')
    with mock.patch('paranormal.parameter_interface.open') as o:
        o.return_value = temp
        to_yaml_file(p, 'mock.yaml', include_defaults=True)
    with open(temp.name) as yaml_file:
        assert yaml_file.read() == 'b: true\ni: 1\nf: 0.5\nr: 10\ne: X\nl:\n- 0\n- 1\n- 2\na:\n- ' \
                                   '0\n- 100\n- 5\n_type: P\n_module: test_parameter_interface\n'

    # test yaml dumping with alphabetical reorder
    p = P(r=10)
    temp = tempfile.NamedTemporaryFile(delete=False, mode='w+t')
    with mock.patch('paranormal.parameter_interface.open') as o:
        o.return_value = temp
        to_yaml_file(p, 'mock.yaml', include_defaults=True, sort_keys=True)
    with open(temp.name) as yaml_file:
        assert yaml_file.read() == '_module: test_parameter_interface\n_type: P\na:\n- 0\n- 100' \
                                   '\n- 5\nb: true\ne: X\nf: 0.5\ni: 1\nl:\n- 0\n- 1\n- 2\nr: 10\n'


def test_to_argparse():

    parser = to_argparse(MySummer)

    # parse with the defaults
    args = parser.parse_args([])
    # dpw was expanded and will still be in the namespace, just as None
    assert args == Namespace(c=Colors.BLUE, do_something_crazy=False, t=60, dpw_s=None,
                             s_start=0, s_stop=None, s_num=15, f=None)

    args = parser.parse_args(
        '--f 120 --c GREEN --s_start 20 --s_stop 600 --s_num 51 --do_something_crazy'.split(' '))
    assert args == Namespace(c='GREEN', do_something_crazy=True, t=60, dpw_s=None,
                             s_start=20, s_stop=600, s_num=51, f=120)

    # try with an argument that isn't part of the parser
    with pytest.raises(SystemExit):
        parser.parse_args(
            '--do_soooomething_crazy --f 120'.split(' '))


    class YearlySchedule(Params):
        winter = MyWinter()
        summer = MySummer(f=360)

    parser = to_argparse(YearlySchedule)
    args = parser.parse_args(
        '--c RED --s 22 --s_start 20 --s_stop 600 --w_start 20 --w_stop 200 --hib'.split(' '))
    assert args == Namespace(c='RED', do_something_crazy=False, dpw_s=None, dpw_w=None, f=None,
                             hib=True, s=22.0, s_num=15, s_start=20.0, s_stop=600.0, t=60,
                             w_num=15, w_start=20.0, w_stop=200.0)

    class YearlySchedule(Params):
        winter = MyWinter()
        summer = MySummer(f=360)
        spring = MySpring()

    to_argparse(YearlySchedule)
    args = parser.parse_args([])
    assert args == Namespace(c=Colors.BLUE, do_something_crazy=False, dpw_s=None, dpw_w=None,
                             f=None, hib=False, s=12, s_num=15, s_start=0, s_stop=None, t=60,
                             w_num=15, w_start=0, w_stop=None)


    # Make sure conflicting params are resolved
    parser = to_argparse(DoubleSweep)
    args = parser.parse_args([])
    assert args == Namespace(f_num=30, f_start=10, f_stop=20, freq_sweep_t_num=50,
                             freq_sweep_t_start=100, freq_sweep_t_stop=200, freq_sweep_times=None,
                             freqs=None, time_sweep_t_num=20, time_sweep_t_start=100,
                             time_sweep_t_stop=500, time_sweep_times=None)

    # make sure check that requires prefixes if expand=True for multiple classes is working
    class BadFreqSweep(Params):
        freqs = LinspaceParam(help='freqs', expand=True)
        times = LinspaceParam(help='times', expand=True)

    with pytest.raises(ValueError):
        to_argparse(BadFreqSweep)


def test_from_parsed_args():
    parser = to_argparse(MyWinter)
    y = from_parsed_args(MyWinter, params_namespace=parser.parse_args([]))[0]
    correct_items = [('s', 12), ('hib', False), ('dpw_w', [0, None, 15])]
    _compare_two_param_item_lists(y.items(), correct_items)

    args = parser.parse_args('--w_stop 10 --w_num 11 --hib --s 35'.split(' '))
    y = from_parsed_args(MyWinter, params_namespace=args)[0]
    correct_items = [('s', 35), ('hib', True), ('dpw_w', np.arange(0, 11))]
    _compare_two_param_item_lists(y.items(), correct_items)

    class YearlySchedule(Params):
        winter = MyWinter()
        summer = MySummer(f=None)

    # test that nested classes work
    parser = to_argparse(YearlySchedule)
    args = parser.parse_args(
        '--c RED --s 22 --s_start 20 --s_stop 600 --w_start 20 --w_stop 200 --hib'.split(' '))
    y = from_parsed_args(YearlySchedule, params_namespace=args)[0]
    correct_items = [('winter', MyWinter(s=22, dpw_w=[20, 200, 15], hib=True)),
                     ('summer', MySummer(c=Colors.RED, dpw_s=[20, 600, 15]))]
    _compare_two_param_item_lists(y.items(), correct_items)

    # test that nested classes with positionals work
    class PositionalsC(Params):
        a_pos = PositionalsA()
        b_pos = PositionalsB()

    parser = to_argparse(PositionalsC)
    args = parser.parse_args(
        '1.0 hey 0.0 1.0 22.0 1 --b 10'.split(' '))
    y = from_parsed_args(PositionalsC, params_namespace=args)[0]
    correct_items = [('a_pos', PositionalsA(x=1.0, z=[0.0, 1.0, 22.0], y='hey')),
                     ('b_pos', PositionalsB(a=1, b=10))]
    _compare_two_param_item_lists(y.items(), correct_items)

    parser = to_argparse(DoubleSweep)

    # make sure if you pass an expanded param, an error is thrown
    with pytest.raises(AssertionError):
        args = parser.parse_args([])
        setattr(args, 'freq_sweep_times', [0, 100, 200])
        from_parsed_args(DoubleSweep, params_namespace=args)

    args = parser.parse_args(
        '--time_sweep_t_start 20 --time_sweep_t_stop 30 --f_stop 40'.split(' '))
    y = from_parsed_args(DoubleSweep, params_namespace=args)[0]
    correct_items = [('freq_sweep', FreqSweep(freqs=[10, 40.0, 30])),
                     ('time_sweep', TimeSweep(times=[20, 30, 20]))]
    _compare_two_param_item_lists(y.items(), correct_items)


def test_create_parser_and_parse_args():
    # test that nested classes with positionals work
    class PositionalsC(Params):
        a_pos = PositionalsA()
        b_pos = PositionalsB()

    correct_items = [('a_pos', PositionalsA(x=1.0, z=[0.0, 1.0, 22.0], y='hey')),
                     ('b_pos', PositionalsB(a=1, b=10))]
    with mock.patch('paranormal.parameter_interface.ArgumentParser.parse_known_args') as pa:
        pa.return_value = (Namespace(b=10, positionals=['1.0', 'hey', '0.0', '1.0', '22.0', '1']),
                           [])
        y = create_parser_and_parse_args(PositionalsC)
    _compare_two_param_item_lists(y.items(), correct_items)

    # test that nested classes work:
    class YearlySchedule(Params):
        winter = MyWinter()
        summer = MySummer(f=None)

    with mock.patch('paranormal.parameter_interface.ArgumentParser.parse_known_args') as pa:
        pa.return_value = (Namespace(c='RED', do_something_crazy=False, dpw_s=None, dpw_w=None,
                                     f=None, hib=True, s=22.0, s_num=15, s_start=20.0, s_stop=600.0,
                                     t=60, w_num=15, w_start=20.0, w_stop=200.0), [])
        y = create_parser_and_parse_args(YearlySchedule)
    correct_items = [('winter', MyWinter(s=22, dpw_w=[20, 200, 15], hib=True)),
                     ('summer', MySummer(c=Colors.RED, dpw_s=[20, 600, 15]))]
    _compare_two_param_item_lists(y.items(), correct_items)

