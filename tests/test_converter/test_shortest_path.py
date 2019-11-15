# -*- coding: utf-8 -*-
"""
pytest for shortest_path.py

History:
    Created on 3 Mar 2018
    @author: Dr. Elias J. Willemse
    @contact: ejwillemse@gmail.com
    @license: GNU GENERAL PUBLIC LICENSE
"""

import pytest
from converter import shortest_path


def test_destination_not_exists_error():
    p_full = [[None, 2, 1, 2, 3, 4]]
    with pytest.raises(AttributeError):
        shortest_path.sp_full(p_full, origin=0, destination=5)


def test_correct_path():
    p_full = [[None, 0, 0, 2, 3, 4]]
    path = shortest_path.sp_full(p_full, origin=0, destination=5)
    assert path == [2, 3, 4]


def test_correct_path_full():
    p_full = [[None, 0, 0, 2, 3, 4]]
    path = shortest_path.sp_full(p_full, origin=0, destination=5, full=True)
    assert path == [0, 2, 3, 4, 5]