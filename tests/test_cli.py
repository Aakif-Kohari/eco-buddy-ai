"""
Unit tests for the EcoBuddy AI CLI suite.
"""

import pytest
import json
import sys
from io import StringIO
from apps.cli.main import main, create_parser


def test_cli_parser_help():
    parser = create_parser()
    assert "carbon" in parser._subparsers._actions[1].choices
    assert "water" in parser._subparsers._actions[1].choices
    assert "meal" in parser._subparsers._actions[1].choices
    assert "convert" in parser._subparsers._actions[1].choices


def test_cli_carbon_command_json(monkeypatch, capsys):
    ret = main(["carbon", "--transport", "Car", "--distance", "15", "--electricity", "200", "--diet", "Vegetarian", "--flights", "0", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "annual_footprint_kg_co2" in data
    assert "eco_score" in data
    assert data["eco_score"] > 0
    assert "recommendations" in data


def test_cli_water_command_json(monkeypatch, capsys):
    ret = main(["water", "--shower", "5", "--laundry", "2", "--diet", "Vegan", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "daily_liters" in data
    assert "annual_liters" in data
    assert data["daily_liters"] > 0


def test_cli_meal_command_json(monkeypatch, capsys):
    ret = main(["meal", "--name", "Quick Tofu Bowl", "--item", "Tofu", "200", "--item", "Rice", "150", "--json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "Quick Tofu Bowl"
    assert data["co2_kg"] > 0
    assert data["water_l"] > 0
    assert len(data["contributions"]) == 2


def test_cli_convert_command(capsys):
    ret = main(["convert", "10", "km", "mi"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "10.0 km =" in captured.out
    assert "mi" in captured.out
