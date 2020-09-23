from tkinter import *
from tkinter.ttk import *

class TkBuilder():
    def __init__(self,):
        self.inspected = None
        self.parent_stack = []

    def push_ui(self, ui_element):
        self.parent_stack.append(ui_element)
    
    def pop_ui(self):
        return self.parent_stack.pop()
    
    def top_ui(self):
        return self.parent_stack[-1]
    
    def root_ui(self):
        return self.parent_stack[0]
    
    def visit(self, visitable):
        return visitable.accept_visitor(self)

    def visit_TextView(self, text_view):
        text = Text(self.top_ui())
        text.insert(END, text_view.text_for(text_view.object_to_display(self.inspected)))
        return text

    def visit_TreeView(self, tree_view):
        tree = Treeview(self.top_ui(), columns=tree_view.column_names())
        tree_view.ui = tree
        tree.heading("#0")
        tree.column("#0", width=40)
        for column_name in tree_view.column_names():
            tree.heading(column_name, text=column_name)
        for root in tree_view.object_to_display(self.inspected):
            item = tree.insert("", "end",
                iid=tree_view.register_binding(root),
                text=tree_view.string_for(root),
                values=tree_view.column_values_for(root))
            for child in tree_view.children_for(root):
                tree.insert(item, "end",
                    iid=tree_view.register_binding(child),
                    text=tree_view.string_for(child),
                    values=tree_view.column_values_for(child))
        
        def open_children(parent):
            tree.item(parent, open=True)
            for child in tree.get_children(parent):
                real_child = tree_view.object_bound_for(child)
                for subchild in tree_view.children_for(real_child):
                    tree.insert(child, "end",
                        iid=tree_view.register_binding(subchild),
                        text=tree_view.string_for(subchild), 
                        values=tree_view.column_values_for(subchild))
        
        def handle_tree_view_open_event(event):
            open_children(tree.focus())
        
        def close_children(parent):
            tree.item(parent, open=False)
            for child in tree.get_children(parent):
                tree.item(child, open=False)
                for subchild in tree.get_children(child):
                    tree_view.unregister_binding(subchild)
                    tree.delete(subchild)
        
        def handle_tree_view_close_event(event):
            close_children(tree.focus())

        def acquire_focus(event):
            print("parents: ", end="")
            for p in tree_view.parents_iter():
                print(p)
            tree_view.parent.parent.navigator.current_inspector = tree_view.parent.parent #TODO make it clean
            event.widget
            tree.focus_set()
        
        def handle_open_key(event):
            if len(event.widget.selection()) == 0:
                print("Nothing selected")
            elif len(event.widget.selection()) > 1:
                print("TODO: handler selection of more than 1 item")
            else:
                selected = event.widget.selection()[0]
                tree_view.navigate(tree_view.object_bound_for(selected))
        
        tree.bind('<<TreeviewOpen>>', handle_tree_view_open_event)
        tree.bind('<<TreeviewClose>>', handle_tree_view_close_event)
        tree.bind('<FocusIn>', acquire_focus)
        tree.bind('<Control-o>', handle_open_key)
        return tree
    
    def visit_ListView(self, list_view):
        l = Listbox(self.top_ui())
        for index, item in enumerate(list_view.items_for(list_view.object_to_display(self.inspected))):
            l.insert(index, item)
        return l
    
    def visit_HorizontalCompositeView(self, horizontal_view):
        f = Frame(self.top_ui())
        self.push_ui(f)
        for index, v in enumerate(horizontal_view.views):
            self.visit(v).pack(fill="x", side="left", expand=True)
        self.pop_ui()
        f.pack(expand=True)
        return f
    
    def visit_VerticalCompositeView(self, vertical_view):
        f = Frame(self.top_ui())
        self.push_ui(f)
        for index, v in enumerate(vertical_view.views):
            self.visit(v).pack(fill="x")
        self.pop_ui()
        f.pack(expand=True)
        return f
    
    def visit_Inspector(self, inspector):
        self.inspected = [inspector.to_inspect] if type(inspector.to_inspect) == list else inspector.to_inspect
        self.push_ui(Notebook(self.top_ui()))
        for view in inspector.views:
            v = self.visit(view)
            self.top_ui().add(v, text=view.title)
        self.top_ui().bind('<<NotebookTabChanged>>', )
        return self.pop_ui()
    
    def visit_InspectorNavigator(self, inspector_navigator):
        self.push_ui(Tk())
        inspector_navigator.ui = self.top_ui()
        self.top_ui().title("pynspector")
        self.visit(inspector_navigator.inspectors[-1]).pack(fill="y", side="left")
        def handle_close_key(event):
            inspector_navigator.pop_inspector()
        self.top_ui().bind("<Control-u>", handle_close_key)
        return self.pop_ui()


def open_inspector(inspector):
    builder = TkBuilder()
    app = builder.visit(inspector)
    app.mainloop()

def add_inspector(inspector_navigator, ui):
    builder = TkBuilder()
    builder.push_ui(ui)
    if len(ui.winfo_children()) > 1:
        for children_to_hide in ui.winfo_children()[:-1]:
            children_to_hide.pack_forget()
    inspector = inspector_navigator.inspectors[-1]
    builder.visit(inspector).pack(fill="y", side="left")
    builder.pop_ui()
    return ui

def remove_inspector(inspector_navigator, ui):
    ui.winfo_children()[-1].destroy()
    for child in ui.winfo_children()[-2:]:
        child.pack_forget()
    for child in ui.winfo_children()[-2:]:
        child.pack(fill="y", side="left")
    return ui