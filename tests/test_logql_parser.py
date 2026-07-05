import pytest

from app.application.query.parser import LogQLParser
from app.domain.enums import MatchOp


class TestLogQLParser:
    def setup_method(self):
        self.parser = LogQLParser()

    def test_parse_single_matcher(self):
        matchers = self.parser.parse('{service="api"}')
        assert len(matchers) == 1
        assert matchers[0].name == "service"
        assert matchers[0].op == MatchOp.EQ
        assert matchers[0].value == "api"

    def test_parse_multiple_matchers(self):
        matchers = self.parser.parse('{service="api", env="prod"}')
        assert len(matchers) == 2
        assert matchers[0].name == "service"
        assert matchers[1].name == "env"

    def test_parse_not_equal_operator(self):
        matchers = self.parser.parse('{level!="DEBUG"}')
        assert len(matchers) == 1
        assert matchers[0].op == MatchOp.NEQ
        assert matchers[0].value == "DEBUG"

    def test_parse_regex_match(self):
        matchers = self.parser.parse('{service=~"api-.*"}')
        assert len(matchers) == 1
        assert matchers[0].op == MatchOp.RE
        assert matchers[0].value == "api-.*"

    def test_parse_negated_regex(self):
        matchers = self.parser.parse('{level!~"TRACE|DEBUG"}')
        assert len(matchers) == 1
        assert matchers[0].op == MatchOp.NRE

    def test_parse_empty_query(self):
        matchers = self.parser.parse("{}")
        assert len(matchers) == 0

    def test_parse_whitespace_query(self):
        matchers = self.parser.parse("  {}  ")
        assert len(matchers) == 0

    def test_parse_invalid_format_no_braces(self):
        with pytest.raises(ValueError, match="Неверный формат"):
            self.parser.parse('service="api"')

    def test_parse_invalid_format_no_matchers(self):
        with pytest.raises(ValueError, match="Не удалось распарсить"):
            self.parser.parse("{invalid}")

    def test_parse_escaped_quotes(self):
        matchers = self.parser.parse('{msg="hello \\"world\\""}')
        assert len(matchers) == 1
        assert matchers[0].value == 'hello "world"'

    def test_parse_complex_query(self):
        matchers = self.parser.parse(
            '{service="api", env="prod", level="ERROR"}'
        )
        assert len(matchers) == 3
        names = {m.name for m in matchers}
        assert names == {"service", "env", "level"}
