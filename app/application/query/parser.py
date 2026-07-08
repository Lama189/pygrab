import re

from app.domain.models import LabelMatcher, MatchOp


class LogQLParser:
    MATCHER_REGEX = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(=|!=|=~|!~)\s*"((?:[^"\\]|\\.)*)"')
    OP_MAP = {
        "=": MatchOp.EQ,
        "!=": MatchOp.NEQ,
        "=~": MatchOp.RE,
        "!~": MatchOp.NRE,
    }

    def parse(self, query: str) -> list[LabelMatcher]:
        query = query.strip()
        if not query:
            return []

        start = query.find("{")
        end = query.find("}", start + 1) if start != -1 else -1

        if start == -1 or end == -1:
            raise ValueError("Неверный формат LogQL запроса")
        
        content = query[start + 1:end].strip()
        if not content:
            return []
        
        matchers = []
        for match in self.MATCHER_REGEX.finditer(content):
            name, op_str, raw_value = match.groups()

            op = self.OP_MAP.get(op_str)
            if not op:
                raise ValueError(f"Неподдерживаемый оператор: {op_str}")
            
            value = raw_value.replace('\\"', '"')
            matchers.append(LabelMatcher(name=name, op=op, value=value))

        if not matchers and content:
            raise ValueError(f"Не удалось распарсить ни одного условия в запросе: {content}")
        
        return matchers
            