import tkui

from abc import ABCMeta, abstractmethod

class InspectorView(metaclass=ABCMeta):
    def __init__(self, parent=None, title="", display=lambda obj: obj, ui=None):
        self.title=title
        self.display=display
        self.parent = parent
        self.ui = ui
    
    @abstractmethod
    def accept_visitor(self, visitor):
        pass
    
    def object_to_display(self, obj):
        return self.display(obj)
    
    def navigate(self, obj):
        self.parent.navigate(obj)
    
    def parents_iter(self):
        if self.parent != None:
            yield self.parent
            self.parent.parents_iter()

class TreeView(InspectorView):
    def __init__(self, children_accessor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children_accessor = children_accessor
        self.string_converter = str
        self.last_id = 0
        self.bindings = dict()
        self.columns=[]
    
    def register_binding(self, obj):
        self.bindings[str(self.last_id)] = obj
        self.last_id += 1
        return str(self.last_id - 1)
    
    def unregister_binding(self, iid):
        del self.bindings[iid]
    
    def object_bound_for(self, iid):
        return self.bindings[iid]
    
    def add_column(self, column_name, accessor):
        self.columns.append(TreeColumn(column_name, accessor))
    
    def accept_visitor(self, visitor):
        return visitor.visit_TreeView(self)
    
    def children_for(self, obj):
        return self.children_accessor(obj)
    
    def string_for(self, obj):
        return self.string_converter(obj)
    
    def column_names(self):
        return [ column.name for column in self.columns ]
    
    def column_values_for(self, obj):
        return [ column.accessor(obj) for column in self.columns ]

class TreeColumn():
    def __init__(self, name, accessor):
        self.name = name
        self.accessor = accessor
    
    def access_for(self, obj):
        return self.accessor(obj)

class TextView(InspectorView):
    def __init__(self, text_accessor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_accessor = text_accessor
    
    def accept_visitor(self, visitor):
        return visitor.visit_TextView(self)
    
    def text_for(self, obj):
        return self.text_accessor(obj)

class ListView(InspectorView):
    def __init__(self, items_accessor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_accessor = items_accessor

    def accept_visitor(self, visitor):
        return visitor.visit_ListView(self)
    
    def items_for(self, obj):
        return self.items_accessor(obj)

class CompositeView(InspectorView):
    def __init__(self, views, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.views = views
        for view in self.views:
            view.parent = self

class HorizontalCompositeView(CompositeView):
    def accept_visitor(self, visitor):
        return visitor.visit_HorizontalCompositeView(self)

class VerticalCompositeView(CompositeView):
    def accept_visitor(self, visitor):
        return visitor.visit_VerticalCompositeView(self)

class Inspector():
    def __init__(self, to_inspect, views=[], navigator=None):
        self.to_inspect = to_inspect
        self._views = None
        self.views = views
        self.navigator = navigator
    
    @property
    def views(self):
        return self._views
    
    @views.setter
    def views(self, views):
        self._views = views
        for view in self.views:
            view.parent = self

    def accept_visitor(self, visitor):
        return visitor.visit_Inspector(self)

    def add_view(self, view):
        self.views.append(view)
    
    def navigate(self, obj):
        self.navigator.push_inspector(inspector_for(obj))

class InspectorNavigator():
    def __init__(self, initial_inspector):
        self._inspectors = None
        self.inspectors = [ initial_inspector ]
        self.current_inspector = self.inspectors[0]
        self.ui = None

    def accept_visitor(self, visitor):
        return visitor.visit_InspectorNavigator(self)
    
    @property
    def inspectors(self):
        return self._inspectors
    
    @inspectors.setter
    def inspectors(self, inspectors):
        self._inspectors = inspectors
        for inspector in self.inspectors:
            inspector.navigator = self
    
    def index_of(self, inspector):
        return self.inspectors.index(inspector)
    
    def push_inspector(self, inspector):
        inspector.navigator = self
        if self.inspectors[-1] is self.current_inspector:
            self.inspectors.append(inspector)
            tkui.add_inspector(self, self.ui)
    
    def pop_inspector(self):
        if len(self.inspectors) <= 1:
            return
        self.inspectors.pop()
        tkui.remove_inspector(self, self.ui)

class RawViewVariable():
    def __init__(self, name, value):
        self.name = name
        self.value = value

def variables_from(obj):
    if type(obj) is list:
        return [ RawViewVariable(str(index), value) for index, value in enumerate(obj) ]
    elif type(obj) is tuple:
        return variables_from(list(obj))

    if(obj.__class__.__module__ == "builtins"): # TODO: this is Python3.7 > specific
        return []
    
    if type(obj) == RawViewVariable:
        return variables_from(obj.value)
    
    return [ RawViewVariable(name, value) for name, value in vars(obj).items() ]

def raw_view():
    """ Returns a views that works for any object. It shows instance variables
        of the object and their value.
    """
    treeview = TreeView(variables_from, display=lambda obj: [obj])
    treeview.string_converter = lambda obj: ""
    treeview.add_column(
        "Variable",
        lambda obj: obj.name if type(obj) == RawViewVariable else "self"
    )
    treeview.add_column(
        "Value",
        lambda obj: obj.value if type(obj) == RawViewVariable else str(obj)
    )
    treeview.add_column(
        "Type",
        lambda obj: str(type(obj.value)) if type(obj) == RawViewVariable else str(type(obj))
    )
    return VerticalCompositeView(
        [treeview, TextView(lambda x: "Python code here")],
        title="Raw")

def meta_view():
    superclasses_view = ListView(lambda obj: type(obj).mro())
    methods_view = ListView(lambda cls:[])#lambda cls: [func for func in dir(cls) if callable(getattr(cls, func))])
    return VerticalCompositeView(
            [HorizontalCompositeView([superclasses_view, methods_view]),
            TextView(lambda x: "Method code here")],
        title="Meta")

def integer_view():
    treeview = TreeView(
        lambda obj: [],
        title="Integer",
        display=lambda i: [("decimal", str(i)), ("hex", hex(i)), ("octal", oct(i)), ("binary", bin(i))]
    )
    treeview.string_converter = lambda obj: ""
    treeview.add_column(
        "Key",
        lambda t: t[0]
    )
    treeview.add_column(
        "Value",
        lambda t: t[1]
    )
    return treeview

class InspectorRegistry():
    def __init__(self):
        self.registry = dict()
    
    def register_view(self, view, obj_type):
        if obj_type not in self.registry:
            self.registry[obj_type] = []
        
        self.registry[obj_type].append(view)
    
    def views_for(self, cls):
        views = []
        for superclass in cls.mro():
            if superclass in self.registry:
                views.extend(self.registry[superclass])
        return list(map(lambda f: f(), views))

def default_registry():
    reg = InspectorRegistry()
    reg.register_view(raw_view, object)
    reg.register_view(meta_view, object)
    reg.register_view(lambda : TextView(lambda s: s, title="Content"), str)
    reg.register_view(integer_view, int)
    return reg

registry = default_registry()
inspector_opener = tkui.open_inspector

def views_for_class(cls):
    global registry
    return registry.views_for(cls)

def inspector_for(obj):
    return Inspector(obj, views_for_class(type(obj)))

def inspect(obj):
    inspector_opener(inspector_for(obj))

if __name__ == "__main__":
    class Foo():
        def __init__(self):
            self.f = [1,2,3]
            self.n = "Lol"
    # inspect(Foo())

    # inspect("Hello world")

    # inspect(42)
    navigator = InspectorNavigator(inspector_for(Foo()))
    # navigator.add_inspector(inspector_for(navigator))
    inspector_opener(navigator)

    # import kernel, views
    # v = VerticalCompositeView([TextView(lambda x: str(x)), TextView(lambda x: str(x))])
    # i = Inspector([v])
    # builder = tkui.TkBuilder(42)
    # app = builder.visit(i)
    # app.mainloop()

    # i = Inspector([ListView(lambda x: [x-1, x, x+1])])
    # builder = TkBuilder(42)
    # app = builder.visit(i)
    # app.mainloop()

    # i = Inspector([TreeView(lambda x: [x-1, x, x+1])])
    # builder = TkBuilder(42)
    # app = builder.visit(i)
    # app.mainloop()

    # to_inspect = TreeView(None)
    # to_inspect = (1,2,3,4,5)
    # to_inspect = [[1,2,3,4,5]]
    # class Foo():
    #     def __init__(self):
    #         self.f = [1,2,3]
    #         self.n = "Lol"
    # to_inspect = Foo()
    # i = Inspector([raw_view(), superclasses_view()])
    # builder = TkBuilder(raw_view())
    # app = builder.visit(i)
    # app.mainloop()
