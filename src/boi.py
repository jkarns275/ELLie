from typing import Any, List, Tuple, Optional, Union

class InterpreterException(Exception):

    def __init__(self, reason: str, span: 'Span' = None):
        super().__init__()

        self.reason = reason
        self.span = Span.EMPTY if span is None else span

    def __str__(self):
        return f"Interpreter Error: {self.reason}.\n" + \
                "note: encountered error here\n" + \
                self.span.slice


class Context:

    def __init__(self):
        self.stack_frames = [{}]

    def push_stack_frame(self):
        new_dict = dict()
        self.stack_frames.append(new_dict)

    def pop_stack_frame(self):
        return self.stack_frames.pop()

    def current_stack_frame(self):
        assert len(self.stack_frames) > 0

        return self.stack_frames[-1]

    def push_args(self, args: List['Var'], values: List['Value']):
        assert len(args) == len(values)

        for arg, value in zip(args, values):
            self.push_var(arg, value)

    def pop_args(self, args: List['Var']):
        return list(map(lambda arg: self.pop_var(arg), args))

    def push_var(self, var: 'Var', value: 'Value'):
        sf = self.current_stack_frame()

        if var.name in sf:
            raise InterpreterException("name shadowing is not supported")
        else:
            sf[var.name] = value
    
    def pop_var(self, var: 'Var') -> 'Value':
        sf = self.current_stack_frame()

        if var.name in sf:
            return sf.pop(var.name)
        else:
            raise InterpreterException("tried to pop var which hasn't been added to the current stack frame", var.span)

    def push_function(self, fn: 'Function'):
        sf = self.current_stack_frame()

        argn = len(fn.args)

        if (fn.name.name, argn) in sf:
            raise InterpreterException(f"function '{fn.name.name}' with {argn} arguments is already defined, and name shadowing is not supported", fn.span)
        else:
            sf[(fn.name.name, argn)] = fn

    def pop_function(self, fn: 'Function'):
        sf = self.current_stack_frame()
        argn = len(fn.args)

        if (fn.name.name, argn) in sf:
            return sf.pop((fn.name.name, argn))
        else:
            raise InterpreterException(f"tried top pop function '{fn.name.name}' with {argn} arguments which hasn't been added to the current stack frame", fn.span)

    def get_stack_frame(self, offset):
        assert offset <= 0

        if len(self.stack_frames) < abs(offset):
            return None

        return self.stack_frames[offset]


    def get_function(self, var: 'Var', argn: int):
        assert argn >= 0

        sf = self.current_stack_frame()
        offset = -1
        
        while sf is not None:
            if (var.name, argn) in sf:
                return sf[(var.name, argn)]

            sf = self.get_stack_frame(offset)
            offset -= 1
        
        raise InterpreterException(f"no such function '{var.name}' with {argn} arguments", var.span)

    def get_var(self, var: 'Var'):

        sf = self.current_stack_frame()
        offset = -1
        
        while sf is not None:
            if var.name in sf:
                return sf[var.name]

            sf = self.get_stack_frame(offset)
            offset -= 1
        
        raise InterpreterException(f"no variable with name '{var.name}'", var.span)

class Span:

    EMPTY = None

    def __init__(self, start, end, slice):
        self.start = start
        self.end = end
        self.slice = slice

Span.EMPTY = Span(0, 0, "")

class AST:

    def __init__(self, span: Span):
        self.span = span
    
    def eval(self, context: Context) -> Any:
        raise Exception("Unimplemented")

    def __str__(self):
        return self.span.slice

class Expr(AST):

    def __init__(self, span: Span):
        super().__init__(span)

class Value(Expr):
    
    def __init__(self, value: float, span: Span):
        super().__init__(span)
        self.value = value

    def eval(self, _context: Context) -> 'Value':
        return self

    def __add__(self, other):
        return self.value + other.value

    def __sub__(self, other):
        return self.value - other.value
    
    def __mul__(self, other):
        return self.value * other.value
    
    def __div__(self, other):
        return self.value / other.value

    def __mod__(self, other):
        return self.value % other.value

    def __pow__(self, other):
        return self.value % other.value

    def __lt__(self, other):
        return self.value < other.value
    
    def __le__(self, other):
        return self.value <= other.value
    
    def __gt__(self, other):
        return self.value > other.value
    
    def __ge__(self, other):
        return self.value >= other.value
    
    def __eq__(self, other):
        return self.value == other.value
    
    def __ne__(self, other):
        return self.value != other.value
    


class Var(Expr):

    def __init__(self, name: str, span: Span):
        super().__init__(span)

        self.name = name
        self.span = span

    def eval(self, context: Context) -> Value:
        return context.get_var(self)

    def __str__(self):
        return self.name

class AdditiveExpr(Expr):

    ADDITION    = 0
    SUBTRACTION = 1

    def __init__(self, lhs: Expr, operator: int, rhs: Expr, span: Span):
        super().__init__(span)

        assert 0 <= operator <= 1 

        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs

    def eval(self, context: Context) -> Value:
        lhs_value = self.lhs.eval(context)
        rhs_value = self.rhs.eval(context)

        new_value = lhs_value + rhs_value
        
        assert type(new_value) == float

        return Value(new_value, self.span)

class ConditionExpr(Expr):

    FALSE_VALUES = [0.0, "", []]

    def __init__(self, condition: Expr, span: Span):
        super().__init__(span)

        self.expr = condition

    def eval(self, context: Context) -> bool:
        return self.expr.eval(context).value not in ConditionExpr.FALSE_VALUES


class ComparisonExpr(Expr):

    GT = 0
    GTE = 1
    LT = 2
    LTE = 3
    EQ = 4
    NEQ = 5

    COMPARISON_FNS = {
        GT:     lambda l, r: l > r,
        GTE:    lambda l, r: l >= r,
        LT:     lambda l, r: l < r,
        LTE:    lambda l, r: l <= r,
        EQ:     lambda l, r: l == r,
        NEQ:    lambda l, r: l != r
    }

    def __init__(self, lhs: Expr, operator: int, rhs: Expr, span: Span):
        super().__init__(span)

        assert 0 <= operator <= 5

        self.lhs = lhs
        self.rhs = rhs
        self.operator = operator

    def eval(self, context: Context):
        return ComparisonExpr.COMPARISON_FNS[self.operator](self.lhs.eval(context), self.rhs.eval(context))


class LambdaExpr(Expr):

    """
    GRAMMAR:
    
    let ~ <name: id> ~ ( <unit> | <args: id+>) ~ = ~ <value: expr> ~ in ~ <body: expr>

    DESC:
    The grammar for this is the same as a normal function, but Functions are found on the
    global scope, lambdas are nested within expressions.
    """

    def __init__(self, name: str, args: List[Var], value: Expr, body: Expr, span: Span):
        super().__init__(span)

        self.name = name
        self.args = args
        self.value = value
        self.body = body

        self.as_fn = Function(Var(name, span), args, value, span, is_lambda=True)
    
    def eval(self, context: Context) -> Value:
        context.push_function(self.as_fn)

        result = self.body.eval(context)

        _fn = context.pop_function(self.as_fn)

        return result

class LetExpr(Expr):

    """
    GRAMMAR:

    let ~ <name: id> ~ = ~ <value: expr> ~ in ~ <body: expr>

    """

    def __init__(self, name: Var, value: Expr, body: Expr, span: Span):
        super().__init__(span)

        self.name = name
        self.value = value
        self.body = body
        self.value = value
    
    def eval(self, context: Context) -> Value:
        val = self.value.eval(context) 
        
        context.push_var(self.name, val)

        body_value = self.body.eval(context)

        context.pop_var(self.name)

        return body_value


class FunctionCall(Expr):
    
    """
    GRAMMAR:

    <name: id> ~ ( <unit> | <args: expr+> )

    """

    def __init__(self, name: Var, argv: List[Expr], span: Span):
        super().__init__(span)

        self.name = name
        self.argv = argv

    def eval(self, context: Context):
        fn = context.get_function(self.name, len(self.argv))
        argv = list(map(lambda exp: exp.eval(context), self.argv))
        fn.set_args(argv)

        return fn.eval(context)


class IfExpr(Expr):

    """
    GRAMMAR:

    if ~ ( <lhs: expr> ~ <operator: cmp_op> ~ <rhs: expr> | <condition: expr> ) ~ then ~
        <true_expr: expr> ~
    else ~
        <false_expr: expr>

    """

    def __init__(self, condition: ConditionExpr, true_expr: Expr, false_expr: Expr, span: Span):
        super().__init__(span)

        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr

    def eval(self, context: Context) -> Value:
        if self.condition.eval(context):
            return self.true_expr.eval(context)
        else:
            return self.false_expr.eval(context)


class Function(AST):

    """
    GRAMMAR:

    let ~ <name: id> ~ ( <unit> | <args: id+> ) ~ = ~ <value: expr> ~ in ~ <body: expr>

    """

    def __init__(self, name: Var, args: List[Var], body: Expr, span: Span, is_lambda: bool = False):
        super().__init__(span)

        self.name = name
        self.args = args
        self.body = body
        self.is_lambda = is_lambda

        self.argv = None
    
    def set_args(self, argv: List[Value]) -> bool:
        if len(argv) != len(self.args):
            raise Exception("Interpreter Error: Calling function with wrong number of arguments.")
        
        self.argv = argv
        return True

    def eval(self, context: Context) -> Value:
        """
        set_args must be called before this function is called
        """

        assert self.argv != None 

        if not self.is_lambda:
            context.push_stack_frame()

        context.push_args(self.args, self.argv)
        
        r = self.body.eval(context)
        
        self.argv = None

        _argv = context.pop_args(self.args)

        if not self.is_lambda:
            context.pop_stack_frame()

        return r


class Program:

    def __init__(self, statements: List[Union[Function, Expr]]):
        self.statements = statements
        self.context = Context()

    def run(self):
        for statement in self.statements:
            ty = type(statement)

            if ty == Function:
                self.context.push_function(statement)
            elif ty == Expr:
                statement.eval(self.context)
            else:
                raise TypeError("Expected Function or Expr")

def success(test_name):
    print(f"\n ╠═ {test_name + ' test':34} :: Okay", end='')

def test_let_expr():
    let_expr = LetExpr(Var("a", Span.EMPTY), Value(5.0, Span.EMPTY), Var("a", Span.EMPTY), Span.EMPTY)

    assert let_expr.eval(Context()).value == 5.0

    success("let_expr")

def test_simple_lambda_expr():
    lambda_expr = LambdaExpr("lambda", [Var("a", Span.EMPTY), Var("b", Span.EMPTY)], AdditiveExpr(Var("a", Span.EMPTY), AdditiveExpr.ADDITION, Var("b", Span.EMPTY), Span.EMPTY),
                                FunctionCall(Var("lambda", Span.EMPTY), [Value(4.0, Span.EMPTY), Value(1.0, Span.EMPTY)], Span.EMPTY), Span.EMPTY)

    assert lambda_expr.eval(Context()).value == 5.0

    success("simple_lambda_expr")

def test_simple_function():
    function_ast = Function(Var("sum", Span.EMPTY), [Var("a", Span.EMPTY), Var("b", Span.EMPTY)], AdditiveExpr(Var("a", Span.EMPTY), AdditiveExpr.ADDITION, Var("b", Span.EMPTY), Span.EMPTY), Span.EMPTY)
    
    program = Program([function_ast])
    program.run()

    function_call_ast = FunctionCall(Var("sum", Span.EMPTY), [Value(4.0, Span.EMPTY), Value(5.0, Span.EMPTY)], Span.EMPTY)

    assert function_call_ast.eval(program.context).value == 9

    success("simple_function")

def test_additive_expr():
    context = Context()
    ast = AdditiveExpr(Value(4.0, Span.EMPTY), AdditiveExpr.ADDITION, Value(4.0, Span.EMPTY), Span.EMPTY)

    assert ast.eval(context).value == 8.0

    success("additive_expr")

def test_condition_expr():
    context = Context()
    test_false_ast = ConditionExpr(Value(0.0, Span.EMPTY), Span.EMPTY)
    test_true_ast = ConditionExpr(Value(1.4, Span.EMPTY), Span.EMPTY)

    assert test_false_ast.eval(context) == False
    assert test_true_ast.eval(context) == True
    
    success("condition_expr")

def test_comparison_expr():
    context = Context()

    test_gt_true = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.GT, Value(-1.0, Span.EMPTY), Span.EMPTY)
    test_gt_false = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.GT, Value(1.0, Span.EMPTY), Span.EMPTY)

    test_gte_true = ComparisonExpr(Value(-1.0, Span.EMPTY), ComparisonExpr.GTE, Value(-1.0, Span.EMPTY), Span.EMPTY)
    test_gte_false = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.GTE, Value(1.0, Span.EMPTY), Span.EMPTY)

    test_lt_true = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.LT, Value(1.0, Span.EMPTY), Span.EMPTY)
    test_lt_false = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.LT, Value(-1.0, Span.EMPTY), Span.EMPTY)

    test_lte_true = ComparisonExpr(Value(1.0, Span.EMPTY), ComparisonExpr.LTE, Value(1.0, Span.EMPTY), Span.EMPTY)
    test_lte_false = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.LTE, Value(-1.0, Span.EMPTY), Span.EMPTY)

    test_eq_true = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.EQ, Value(0.0, Span.EMPTY), Span.EMPTY)
    test_eq_false = ComparisonExpr(Value(-1.0, Span.EMPTY), ComparisonExpr.EQ, Value(1.0, Span.EMPTY), Span.EMPTY)
    
    test_neq_true = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.NEQ, Value(-1.0, Span.EMPTY), Span.EMPTY)
    test_neq_false = ComparisonExpr(Value(0.0, Span.EMPTY), ComparisonExpr.NEQ, Value(0.0, Span.EMPTY), Span.EMPTY)

    assert test_gt_true.eval(context) == True
    assert test_gt_false.eval(context) == False

    assert test_gte_true.eval(context) == True
    assert test_gte_false.eval(context) == False

    assert test_lt_true.eval(context) == True
    assert test_lt_false.eval(context) == False

    assert test_lte_true.eval(context) == True
    assert test_lte_false.eval(context) == False

    assert test_eq_true.eval(context) == True
    assert test_eq_false.eval(context) == False

    assert test_neq_true.eval(context) == True
    assert test_neq_false.eval(context) == False

    success("comparison_expr")