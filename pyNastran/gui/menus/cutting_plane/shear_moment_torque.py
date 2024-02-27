"""
The preferences menu handles:
 - Font Size
 - Background Color
 - Text Color
 - Annotation Color
 - Annotation Size
 - Clipping Min
 - Clipping Max

"""
from __future__ import annotations
import os
from typing import Callable, TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QLabel, QPushButton, QGridLayout, QApplication, QHBoxLayout, QVBoxLayout,
    QColorDialog, QLineEdit, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QFrame)

from qtpy.QtGui import QColor


from pyNastran.utils.locale import func_str
from pyNastran.gui.utils.qt.pydialog import PyDialog, QFloatEdit, make_font, check_color
from pyNastran.gui.utils.qt.resize_qtextedit import AutoResizingTextEdit
from pyNastran.gui.utils.qt.qcombobox import make_combo_box # get_combo_box_text # set_combo_box_text,
from pyNastran.gui.utils.qt.qpush_button_color import QPushButtonColor
from pyNastran.gui.utils.qt.dialogs import save_file_dialog
from pyNastran.gui.utils.qt.checks.qlineedit import check_save_path, check_float
from pyNastran.gui.menus.cutting_plane.cutting_plane import get_zaxis
from pyNastran.gui.utils.wildcards import wildcard_csv
if TYPE_CHECKING:  # pragma: no cover
    from .shear_moment_torque_object import ShearMomentTorqueObject
    from pyNastran.gui.typing import ColorInt, ColorFloat
    from pyNastran.gui.main_window import MainWindow

IS_DEMO = False  # just for testing
#IS_DEMO = False
class ShearMomentTorqueWindow(PyDialog):
    """
    +-------------------------+
    | ShearMomentTorqueWindow |
    +-------------------------+
    | Origin      cid  x y z  |
    | P2          cid  x y z  |
    | z-axis      cid  x y z  |
    | tol         cid  x y z  |
    |                         |
    |    Apply OK Cancel      |
    +-------------------------+
    """
    def __init__(self, data, win_parent=None):
        """
        Saves the data members from data and
        performs type checks
        """
        PyDialog.__init__(self, data, win_parent)

        self._updated_preference = False

        self._default_font_size = data['font_size']

        #self.dim_max = data['dim_max']
        self.model_name = data['model_name']
        self.cids = data['cids']
        self.gpforce = data['gpforce']
        #self._origin = data['origin']
        #self._p1 = data['origin']
        #self._p2 = data['origin']

        #self.out_data = data

        self.plane_color_float, self.plane_color_int = check_color(
            data['plane_color'])
        self.plane_opacity = data['plane_opacity']
        self.methods = ['Vector', 'CORD2R']
        #self.zaxis_methods = ['Global Z', 'Camera Normal', 'Manual']
        self.zaxis_methods = ['Manual', 'Global Z']

        self._icord2r = self.methods.index('CORD2R')
        self._imanual = self.zaxis_methods.index('Manual')
        self._zaxis_method = 0  # Global Z - nope...

        self.setWindowTitle('Shear, Moment, Torque')
        self.create_widgets()
        self.create_layout()
        self.set_connections()
        self.on_font(self._default_font_size)
        #self.on_gradient_scale()
        #self.show()

    def on_font(self, value=None) -> None:
        """update the font for the current window"""
        if value in (0, None):
            value = self.font_size_edit.value()
        font = make_font(value, is_bold=False)
        self.setFont(font)

    def set_font_size(self, font_size: int) -> None:
        """
        Updates the font size of all objects in the PyDialog

        Parameters
        ----------
        font_size : int
            the font size
        """
        if self.font_size == font_size:
            return
        self.font_size = font_size
        font = make_font(font_size, is_bold=False)
        self.setFont(font)
        self.set_bold_font(font_size)

    def set_bold_font(self, font_size: int) -> None:
        """
        Updates the font size of all bolded objects in the dialog

        Parameters
        ----------
        font_size : int
            the font size
        """
        bold_font = make_font(font_size, is_bold=True)

        self.additional_params_label.setFont(bold_font)
        self.case_info_label.setFont(bold_font)
        self.plane_label.setFont(bold_font)

        self.location_label.setFont(bold_font)
        self.cid_label.setFont(bold_font)
        self.x_label.setFont(bold_font)
        self.y_label.setFont(bold_font)
        self.z_label.setFont(bold_font)

        self.plot_info.setFont(bold_font)

    def create_widgets(self) -> None:
        """creates the display window"""
        # CORD2R
        #self.origin_label = QLabel("Origin:")
        #self.zaxis_label = QLabel("Z Axis:")
        #self.xz_plane_label = QLabel("XZ Plane:")

        desc = AutoResizingTextEdit(
            'Creates a shear force/bending moment diagram by creating '
            'a series of section cuts.')
        desc.append('')
        desc.append(' 1. Create a vector to march down (from the origin/start '
                    'to end) by defining two points.')
        desc.append('')
        desc.append(
            ' 2. Define an output coordinate system about the origin/start.')
        desc.append(
            'The goal is to orient the cutting plane in the direction that '
            'want to expose forces/moments.')
        desc.append('In other words, point the x-axis roughly down the '
                    'march axis to define what torque is.')
        desc.append('')
        desc.setReadOnly(True)
        desc.viewport().setAutoFillBackground(False)
        desc.setFrameStyle(QFrame.NoFrame)

        self.description = desc

        # Z-Axis Projection
        self.p1_label = QLabel('Origin:')
        self.p3_label = QLabel('End:')
        self.p2_label = QLabel('XZ Plane:')
        self.p1_label.setToolTip('Defines the starting point for the shear, moment, torque plot')
        self.p3_label.setToolTip('Defines the end point for the shear, moment, torque plot')
        self.p2_label.setToolTip('Defines the XZ plane for the shears/moments')

        self.zaxis_label = QLabel('Z Axis:')

        self.method_pulldown = QComboBox()
        for method in self.methods:
            self.method_pulldown.addItem(method)

        self.zaxis_method_pulldown = QComboBox()
        self.zaxis_method_pulldown.setToolTip(
            'Define the output coordinate system\n'
            ' - "Start to XZ-Plane" defines x-axis\n\n'
            'Options for Z-Axis:\n'
            ' - Global Z: z=<0, 0, 1>\n'
            #' - Camera Normal: depends on orientation of model (out of the page)\n'
            ' - Manual: Explicitly define the z-axis'
        )
        for method in self.zaxis_methods:
            self.zaxis_method_pulldown.addItem(method)

        self.cid_label = QLabel('Coordinate System:')
        self.p1_cid_pulldown = QComboBox()
        self.p2_cid_pulldown = QComboBox()
        self.p3_cid_pulldown = QComboBox()
        self.zaxis_cid_pulldown = QComboBox()

        cid_global_str = '0/Global'
        for cid in sorted(self.cids):
            if cid == 0:
                cid_str = cid_global_str
            else:
                cid_str = str(cid)
            #print('cid_str = %r' % cid_str)
            self.p1_cid_pulldown.addItem(cid_str)
            self.p2_cid_pulldown.addItem(cid_str)
            self.p3_cid_pulldown.addItem(cid_str)
            self.zaxis_cid_pulldown.addItem(cid_str)

        self.p1_cid_pulldown.setCurrentIndex(0)
        self.p2_cid_pulldown.setCurrentIndex(0)
        self.p3_cid_pulldown.setCurrentIndex(0)
        self.zaxis_cid_pulldown.setCurrentIndex(0)
        if len(self.cids) == 1:
            self.p1_cid_pulldown.setEnabled(False)
            self.p2_cid_pulldown.setEnabled(False)
            self.p3_cid_pulldown.setEnabled(False)
            self.zaxis_cid_pulldown.setEnabled(False)

        #self.p1_cid_pulldown.setItemText(0, cid_str)
        #self.p2_cid_pulldown.setItemText(0, cid_str)
        #self.zaxis_cid_pulldown.setItemText(0, cid_str)

        self.p1_cid_pulldown.setToolTip('Defines the coordinate system for Point P1/starting point')
        self.p2_cid_pulldown.setToolTip('Defines the coordinate system for Point P2/xz-plane point')
        self.p3_cid_pulldown.setToolTip('Defines the coordinate system for Point P3/ending point')
        self.zaxis_cid_pulldown.setToolTip('Defines the coordinate system for the Z Axis')

        self.p1_x_edit = QFloatEdit('')
        self.p1_y_edit = QFloatEdit('')
        self.p1_z_edit = QFloatEdit('')

        self.p2_x_edit = QFloatEdit('')
        self.p2_y_edit = QFloatEdit('')
        self.p2_z_edit = QFloatEdit('')

        self.p3_x_edit = QFloatEdit('')
        self.p3_y_edit = QFloatEdit('')
        self.p3_z_edit = QFloatEdit('')

        self.zaxis_x_edit = QFloatEdit('')
        self.zaxis_y_edit = QFloatEdit('')
        self.zaxis_z_edit = QFloatEdit('')

        self.additional_params_label = QLabel('Plane Parameters:')
        self.case_info_label = QLabel('Case Info:')

        self.p2_label = QLabel('XZ Plane:')

        # Plane Color
        self.plane_color_label = QLabel('Plane Color:')
        self.plane_color_edit = QPushButtonColor(self.plane_color_int)

        self.plane_opacity_label = QLabel('Plane Opacity:')
        self.plane_opacity_edit = QDoubleSpinBox()
        self.plane_opacity_edit.setRange(0.1, 1.0)
        self.plane_opacity_edit.setDecimals(2)
        self.plane_opacity_edit.setSingleStep(0.05)
        self.plane_opacity_edit.setValue(self.plane_opacity)

        self.flip_coord_label = QLabel('Flip Coordinate System:')
        self.flip_coord_checkbox = QCheckBox()

        #-----------------------------------------------------------------------
        self.time_label = QLabel('Time:')
        if self.gpforce is None:  # pragma: no cover
            # for debugging; not real
            times = ['0.', '0.5', '1.' , '1.5', '2.']
            time = '0.'
        else:
            times = [func_str(time) for time in self.gpforce._times]
            time = times[0]
        self.times_pulldown = make_combo_box(times, time)
        self.time_label.setEnabled(False)
        self.times_pulldown.setEnabled(False)

        #self.node_label = QLabel('Nodes:')
        #self.node_edit = QNodeEdit(self.win_parent, self.model_name, parent=self.gui,
                                   #pick_style='area', tab_to_next=False)

        #self.element_label = QLabel('Elements:')
        #self.element_edit = QElementEdit(self.win_parent, self.model_name, parent=self.gui,
                                         #pick_style='area', tab_to_next=False)

        #self.node_element_label = QLabel('Nodes/Elements:')
        #self.node_element_edit = QLineEdit()
        #self.node_element_edit.setReadOnly(True)

        self.nplanes_label = QLabel('Num Planes:')
        self.nplanes_spinner = QSpinBox()
        self.nplanes_spinner.setMinimum(2)
        self.nplanes_spinner.setMaximum(500)
        self.nplanes_spinner.setValue(20)

        #-----------------------------------------------------------------------
        self.method_label = QLabel('Method:')
        self.plane_label = QLabel('Plane:')
        self.location_label = QLabel('Location:')
        self.zaxis_method_label = QLabel('Z-Axis Method:')
        self.cid_label = QLabel('Coordinate System:')
        self.x_label = QLabel('X')
        self.y_label = QLabel('Y')
        self.z_label = QLabel('Z')

        if 'Z-Axis Projection' not in self.methods:
            self.zaxis_method_label.setVisible(False)

        #self.location_label.setAlignment(Qt.AlignCenter)
        self.cid_label.setAlignment(Qt.AlignCenter)

        self.x_label.setAlignment(Qt.AlignCenter)
        self.y_label.setAlignment(Qt.AlignCenter)
        self.z_label.setAlignment(Qt.AlignCenter)

        self.export_checkbox = QCheckBox()
        self.csv_label = QLabel('CSV Filename:')
        self.csv_edit = QLineEdit()
        self.csv_button = QPushButton('Browse...')

        default_dirname = os.getcwd()
        if self.win_parent is not None:
            default_dirname = self.win_parent.last_dir
        default_filename = os.path.join(default_dirname, 'shear_moment_torque.csv')
        self.csv_edit.setText(default_filename)

        #self.csv_label.setEnabled(False)
        self.csv_edit.setEnabled(False)
        self.csv_button.setEnabled(False)
        #-----------------------------------------------------------------------
        # nodes
        self.add_button = QPushButton('Add')
        self.remove_button = QPushButton('Remove')

        # elements
        self.add2_button = QPushButton('Add')
        self.remove2_button = QPushButton('Remove')
        #-----------------------------------------------------------------------
        self.plot_info = QLabel('Plot Info:')
        self.force_unit_label = QLabel('Force Unit')
        self.moment_unit_label = QLabel('Moment Unit')
        self.force_scale_label = QLabel('Force Scale')
        self.moment_scale_label = QLabel('Moment Scale')

        self.force_unit_edit = QLineEdit('')
        self.moment_unit_edit = QLineEdit('')
        self.force_scale_edit = QFloatEdit('1.0')
        self.moment_scale_edit = QFloatEdit('1.0')

        self.force_unit_edit.setToolTip('Define the force unit for the output')
        self.moment_unit_edit.setToolTip('Define the moment unit for the output')
        self.force_scale_edit.setToolTip('Scale the output force by this')
        self.moment_scale_edit.setToolTip('Scale the output moment by this')
        #-----------------------------------------------------------------------
        # closing
        self.plot_plane_button = QPushButton('Plot Plane')
        self.clear_plane_button = QPushButton('Clear Plane')
        self.apply_button = QPushButton('Apply')
        self.cancel_button = QPushButton('Cancel')
        self.set_bold_font(self._default_font_size)

        if IS_DEMO:  # pragma: no cover
            if 1:
                # bwb
                self.p1_x_edit.setText('1389')
                self.p1_y_edit.setText('1262')
                self.p1_z_edit.setText('87')

                self.p3_x_edit.setText('911')
                self.p3_y_edit.setText('0.1')
                self.p3_z_edit.setText('0.')

                self.p2_x_edit.setText('0')
                self.p2_y_edit.setText('-1')
                self.p2_z_edit.setText('0')
                self.nplanes_spinner.setValue(50)

            elif 0:  # solid_shell_bar
                self.p1_x_edit.setText('0')
                self.p1_y_edit.setText('0')
                self.p1_z_edit.setText('-2')

                self.p3_x_edit.setText('0')
                self.p3_y_edit.setText('0')
                self.p3_z_edit.setText('3')

                self.p2_x_edit.setText('0')
                self.p2_y_edit.setText('1')
                self.p2_z_edit.setText('0')
                self.nplanes_spinner.setValue(5)

    @property
    def gui(self) -> MainWindow:
        if self.win_parent is None:
            return None
        return self.win_parent.parent.gui

    def create_layout(self) -> None:
        """sets up the window"""
        grid = self._make_grid_layout()

        #hbox_csv = QHBoxLayout()
        grid2 = QGridLayout()
        #irow = 0

        #grid2.addWidget(self.node_label, irow, 0)
        #grid2.addWidget(self.node_edit, irow, 1)
        #grid2.addWidget(self.add_button, irow, 2)
        #grid2.addWidget(self.remove_button, irow, 3)
        #irow += 1

        #grid2.addWidget(self.element_label, irow, 0)
        #grid2.addWidget(self.element_edit, irow, 1)
        #grid2.addWidget(self.add2_button, irow, 2)
        #grid2.addWidget(self.remove2_button, irow, 3)
        #irow += 1

        #grid2.addWidget(self.node_element_label, irow, 0)
        #grid2.addWidget(self.node_element_edit, irow, 1)
        #irow += 1

        hbox_csv = QHBoxLayout()
        hbox_csv.addWidget(self.export_checkbox)
        hbox_csv.addWidget(self.csv_label)
        hbox_csv.addWidget(self.csv_edit)
        hbox_csv.addWidget(self.csv_button)
        #----------------------------------------------

        ok_cancel_box = QHBoxLayout()
        ok_cancel_box.addWidget(self.plot_plane_button)
        ok_cancel_box.addWidget(self.clear_plane_button)
        ok_cancel_box.addWidget(self.apply_button)
        ok_cancel_box.addWidget(self.cancel_button)

        vbox = QVBoxLayout()

        vbox.addWidget(self.description)
        vbox.addLayout(grid)
        vbox.addLayout(grid2)
        #vbox.addStretch()
        vbox.addLayout(hbox_csv)
        vbox.addStretch()

        #-----------------------
        #vbox.addLayout(add_remove_box)
        vbox.addLayout(ok_cancel_box)
        self.on_method(0)  # self._icord2r
        self.on_zaxis_method(self._imanual)
        self.setLayout(vbox)

    def on_export_checkbox(self) -> None:
        """this is called when the checkbox is clicked"""
        is_checked = self.export_checkbox.isChecked()
        self.csv_label.setEnabled(is_checked)
        self.csv_edit.setEnabled(is_checked)
        self.csv_button.setEnabled(is_checked)

    def on_browse_csv(self) -> None:
        """opens a file dialog"""
        default_filename = self.csv_edit.text()
        csv_filename, wildcard = save_file_dialog(
            self, 'Select the file name for export',
            default_filename, wildcard_csv)
        if not csv_filename:
            return

        if self.win_parent is not None:
            last_dir = os.path.dirname(csv_filename)
            self.win_parent.load_actions._set_last_dir(last_dir)
        self.csv_edit.setText(csv_filename)

    def _make_grid_layout(self) -> QGridLayout:
        """builds the QGridLayout"""
        grid = QGridLayout()
        irow = 0
        #-------------------------
        grid.addWidget(self.location_label, irow, 0)
        grid.addWidget(self.cid_label, irow, 1)
        grid.addWidget(self.x_label, irow, 2)
        grid.addWidget(self.y_label, irow, 3)
        grid.addWidget(self.z_label, irow, 4)
        irow += 1

        add_row(irow, grid,
                self.p1_label,
                self.p1_cid_pulldown,
                self.p1_x_edit, self.p1_y_edit, self.p1_z_edit)
        irow += 1

        add_row(irow, grid,
                self.p3_label,
                self.p3_cid_pulldown,
                self.p3_x_edit, self.p3_y_edit, self.p3_z_edit)
        irow += 1

        grid.addWidget(self.plane_label, irow, 0)
        irow += 1

        grid.addWidget(self.method_label, irow, 0)
        grid.addWidget(self.method_pulldown, irow, 1)
        irow += 1

        grid.addWidget(self.zaxis_method_label, irow, 0)
        grid.addWidget(self.zaxis_method_pulldown, irow, 1)
        irow += 1

        add_row(irow, grid,
                self.zaxis_label,
                self.zaxis_cid_pulldown,
                self.zaxis_x_edit, self.zaxis_y_edit, self.zaxis_z_edit)
        irow += 1

        add_row(irow, grid,
                self.p2_label,
                self.p2_cid_pulldown,
                self.p2_x_edit, self.p2_y_edit, self.p2_z_edit)
        irow += 1

        #-----------------------------------------
        grid.addWidget(self.case_info_label, irow, 0)
        irow += 1

        grid.addWidget(self.time_label, irow, 0)
        grid.addWidget(self.times_pulldown, irow, 1)
        irow += 1

        grid.addWidget(self.nplanes_label, irow, 0)
        grid.addWidget(self.nplanes_spinner, irow, 1)
        irow += 1

        #-----------------------------------------
        grid.addWidget(self.additional_params_label, irow, 0)
        irow += 1

        grid.addWidget(self.plane_color_label, irow, 0)
        grid.addWidget(self.plane_color_edit, irow, 1)
        irow += 1

        grid.addWidget(self.plane_opacity_label, irow, 0)
        grid.addWidget(self.plane_opacity_edit, irow, 1)
        irow += 1
        # -----------------------------------------
        grid.addWidget(self.plot_info, irow, 0)
        irow += 1

        grid.addWidget(self.force_unit_label, irow, 0)
        grid.addWidget(self.force_unit_edit, irow, 1)
        irow += 1

        grid.addWidget(self.force_scale_label, irow, 0)
        grid.addWidget(self.force_scale_edit, irow, 1)
        irow += 1

        grid.addWidget(self.moment_unit_label, irow, 0)
        grid.addWidget(self.moment_unit_edit, irow, 1)
        irow += 1

        grid.addWidget(self.moment_scale_label, irow, 0)
        grid.addWidget(self.moment_scale_edit, irow, 1)
        irow += 1

        #----------------------------------------------
        return grid

    def set_connections(self) -> None:
        """creates the actions for the menu"""
        self.method_pulldown.currentIndexChanged.connect(self.on_method)
        self.zaxis_method_pulldown.currentIndexChanged.connect(self.on_zaxis_method)
        self.plane_color_edit.clicked.connect(self.on_plane_color)
        self.plane_opacity_edit.valueChanged.connect(self.on_plane_opacity)

        self.export_checkbox.clicked.connect(self.on_export_checkbox)
        self.csv_button.clicked.connect(self.on_browse_csv)
        #self.csv_label.clicked.connect(self.on_export_checkbox)

        self.plot_plane_button.clicked.connect(self.on_plot_plane)
        self.clear_plane_button.clicked.connect(self.on_clear_plane)
        self.apply_button.clicked.connect(self.on_apply)
        self.cancel_button.clicked.connect(self.on_cancel)

    def on_method(self, method_int=None) -> None:
        method = get_pulldown_text(method_int, self.methods, self.method_pulldown)

        is_p2_cid_enabled = True
        is_zaxis_cid_enabled = True
        zaxis_method_visible = False
        if method == 'CORD2R':
            self._zaxis_method = self.zaxis_method_pulldown.currentIndex()
            # set to manual
            #self.on_zaxis_method(method_int=2)  # manual

            self.plane_label.setText('Points on Plane:')
            self.zaxis_label.setText('Origin + Z Axis:')
            self.p2_label.setText('Origin + XZ Plane:')

            #self.zaxis_method_label.setText('Origin + Z-Axis')
            self.zaxis_method_pulldown.setCurrentIndex(self._imanual)
            self.on_zaxis_method()  # update

        elif method == 'Vector':
            is_p2_cid_enabled = False
            is_zaxis_cid_enabled = False
            self.plane_label.setText('Vectors:')
            self.zaxis_label.setText('Z Axis:')
            self.p2_label.setText('XZ Plane Axis:')
            #self.zaxis_method_label.setText('Z-Axis')
            self.zaxis_method_pulldown.setCurrentIndex(self._imanual)
            self.on_zaxis_method()  # update

        elif method == 'Z-Axis Projection':
            #is_p2_cid_enabled = False
            is_zaxis_cid_enabled = False
            zaxis_method_visible = True
            self.plane_label.setText('Point on Plane/Vector:')
            self.zaxis_label.setText('Z Axis:')
            self.p2_label.setText('Origin + XZ Plane:')

            #self.zaxis_method_label.setText('Z-Axis')
            self.zaxis_method_pulldown.setCurrentIndex(self._zaxis_method)
            self.on_zaxis_method()  # update
        else:  # pragma: no cover
            raise NotImplementedError(method)

        self.p2_cid_pulldown.setEnabled(is_p2_cid_enabled)
        self.zaxis_cid_pulldown.setEnabled(is_zaxis_cid_enabled)

        self.zaxis_method_pulldown.setEnabled(zaxis_method_visible)
        self.zaxis_method_pulldown.setVisible(zaxis_method_visible)
        self.zaxis_method_label.setEnabled(zaxis_method_visible)

    def on_zaxis_method(self, method_int=None) -> None:
        method = get_pulldown_text(method_int, self.zaxis_methods,
                                   self.zaxis_method_pulldown)

        if method == 'Global Z':
            is_visible = False
        #elif method == 'Camera Normal':
            #is_visible = False
        elif method == 'Manual':
            is_visible = True
        else:  # pragma: no cover
            raise NotImplementedError(method)

        self.zaxis_cid_pulldown.setVisible(is_visible)
        self.zaxis_x_edit.setVisible(is_visible)
        self.zaxis_y_edit.setVisible(is_visible)
        self.zaxis_z_edit.setVisible(is_visible)

    def on_plane_opacity(self) -> None:
        """ Sets the plane opacity"""
        opacity = self.plane_opacity_edit.value()
        if self.win_parent is not None:
            obj: ShearMomentTorqueObject = self.win_parent.shear_moment_torque_obj
            obj.set_plane_properties(opacity, self.plane_color_float)

    def on_plane_color(self) -> None:
        """ Choose a plane color"""
        title = 'Choose a cutting plane color'
        rgb_color_ints = self.plane_color_int
        color_edit = self.plane_color_edit
        func_name = 'set_plane_color'
        passed, rgb_color_ints, rgb_color_floats = self._background_color(
            title, color_edit, rgb_color_ints, func_name)
        if passed:
            self.plane_color_int = rgb_color_ints
            self.plane_color_float = rgb_color_floats
            self.on_plane_opacity()

    def _background_color(self, title: str,
                          color_edit: QPushButtonColor,
                          rgb_color_ints: ColorInt,
                          func_name: Callable) -> tuple[bool, ColorInt, ColorFloat]:
        """
        helper method for:
         - ``on_background_color``
         - ``on_background_color2``

        """
        passed, rgb_color_ints, rgb_color_floats = self.on_color(
            color_edit, rgb_color_ints, title)
        #if passed and 0:
            #if self.win_parent is not None:
                #settings = self.win_parent.settings
                #func_background_color = getattr(settings, func_name)
                #func_background_color(rgb_color_floats)
        return passed, rgb_color_ints, rgb_color_floats

    def on_color(self, color_edit,
                 rgb_color_ints: ColorInt,
                 title: str) -> tuple[bool, ColorInt, ColorFloat]:
        """pops a color dialog"""
        qcolor = QColor(*rgb_color_ints)
        col = QColorDialog.getColor(qcolor, self, title)
        if not col.isValid():
            return False, rgb_color_ints, None

        color_float: ColorFloat = col.getRgbF()[:3]  # floats
        color_int = [int(colori * 255) for colori in color_float]

        assert isinstance(color_float[0], float), color_float
        assert isinstance(color_int[0], int), color_int

        color_edit.setStyleSheet(
            'QPushButton {'
            'background-color: rgb(%s, %s, %s);' % tuple(color_int) +
            #"border:1px solid rgb(255, 170, 255); "
            '}')
        return True, color_int, color_float


    #---------------------------------------------------------------------------

    def on_validate(self) -> bool:
        p1_cidi = self.p1_cid_pulldown.currentText()
        p2_cidi = self.p2_cid_pulldown.currentText()
        p3_cidi = self.p3_cid_pulldown.currentText()
        zaxis_cidi = self.zaxis_cid_pulldown.currentText()
        p1_cid = int(p1_cidi) if 'Global' not in p1_cidi else 0
        p2_cid = int(p2_cidi) if 'Global' not in p2_cidi else 0
        p3_cid = int(p3_cidi) if 'Global' not in p3_cidi else 0
        zaxis_cid = int(zaxis_cidi) if 'Global' not in zaxis_cidi else 0
        #print('p1_cidi=%r p2_cidi=%r p3_cidi=%r' % (p1_cidi, p2_cidi, zaxis_cidi))
        #print('p2_cid=%r p2_cid=%r p3_cidi=%r' % (p2_cid, p2_cid, zaxis_cid))

        p1_x, flag1 = check_float(self.p1_x_edit)
        p1_y, flag2 = check_float(self.p1_y_edit)
        p1_z, flag3 = check_float(self.p1_z_edit)

        p2_x, flag4 = check_float(self.p2_x_edit)
        p2_y, flag5 = check_float(self.p2_y_edit)
        p2_z, flag6 = check_float(self.p2_z_edit)

        p3_x, flag7 = check_float(self.p3_x_edit)
        p3_y, flag8 = check_float(self.p3_y_edit)
        p3_z, flag9 = check_float(self.p3_z_edit)
        p1 = [p1_x, p1_y, p1_z]
        p2 = [p2_x, p2_y, p2_z]
        p3 = [p3_x, p3_y, p3_z]

        flag10, flag11, flag12, zaxis_cid, zaxis = get_zaxis(
            self.win_parent, # for camera
            self.zaxis_method_pulldown,
            self.zaxis_x_edit, self.zaxis_y_edit, self.zaxis_z_edit)

        method = self.method_pulldown.currentText()
        assert method in self.methods, f'method={method!r}'
        flag13 = True

        plane_opacity = self.plane_opacity_edit.value()
        nplanes = self.nplanes_spinner.value()

        csv_filename = None
        csv_flag = True
        if self.export_checkbox.isChecked():
            csv_filename, csv_flag = check_save_path(self.csv_edit)

        force_scale, force_flag = check_float(self.force_scale_edit)
        moment_scale, moment_flag = check_float(self.moment_scale_edit)
        flags = [
            flag1, flag2, flag3, flag4, flag5, flag6, flag7, flag8, flag9,
            flag10, flag11, flag12,
            flag13, csv_flag,
            force_flag, moment_flag]

        force_unit = self.force_unit_edit.text()
        moment_unit = self.moment_unit_edit.text()
        #force_scale = 1.
        #moment_scale = 1.
        if all(flags):
            # Z-Axis Method
            # p1: origin
            # p2: xz_plane
            # p3: end
            self.out_data['method'] = method
            self.out_data['p1'] = [p1_cid, p1]  # origin
            self.out_data['p2'] = [p2_cid, p2]  # xzplane
            self.out_data['p3'] = [p3_cid, p3]  # end
            self.out_data['zaxis'] = [zaxis_cid, zaxis]
            self.out_data['plane_color'] = self.plane_color_float
            self.out_data['plane_opacity'] = plane_opacity
            self.out_data['nplanes'] = nplanes
            self.out_data['csv_filename'] = csv_filename
            self.out_data['force'] = [force_scale, force_unit]
            self.out_data['moment'] = [moment_scale, moment_unit]
            self.out_data['clicked_ok'] = True
            return True
        return False

    def on_clear_plane(self) -> None:
        if self.win_parent is not None:
            obj: ShearMomentTorqueObject = self.win_parent.shear_moment_torque_obj
            obj.on_clear_plane_actors()
        return

    def on_plot_plane(self) -> bool:
        passed = self.on_validate()
        if passed and self.win_parent is not None:
            obj: ShearMomentTorqueObject = self.win_parent.shear_moment_torque_obj
            obj.make_plane_from_data(self.out_data)
            #self.win_parent.make_smt_from_data(self.out_data)
        return passed

    def on_apply(self) -> bool:
        passed = self.on_validate()
        if passed and self.win_parent is not None:
            obj: ShearMomentTorqueObject = self.win_parent.shear_moment_torque_obj
            obj.make_smt_from_data(self.out_data, show=True)
            #self.win_parent.make_smt_from_data(self.out_data)
        return passed

    def on_cancel(self) -> None:
        self.out_data['close'] = True
        self.close()

def add_row(irow: int,
            grid: QGridLayout,
            p1_label, p1_cid_pulldown,
            p1_x_edit, p1_y_edit, p1_z_edit) -> None:
    """adds the items to the grid"""
    grid.addWidget(p1_label, irow, 0)
    grid.addWidget(p1_cid_pulldown, irow, 1)
    grid.addWidget(p1_x_edit, irow, 2)
    grid.addWidget(p1_y_edit, irow, 3)
    grid.addWidget(p1_z_edit, irow, 4)


def get_pulldown_text(method_int: int,
                      methods: list[str],
                      pulldown: QComboBox):
    if method_int is None:
        #method = pulldown.getText()
        method = pulldown.currentText()
    else:
        method = methods[method_int]
    return method

def main() -> None:  # pragma: no cover
    # kills the program when you hit Cntl+C from the command line
    # doesn't save the current state as presumably there's been an error
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)


    import sys
    # Someone is launching this directly
    # Create the QApplication
    app = QApplication(sys.argv)
    #The Main window

    gpforce = None
    data = {
        'font_size' : 8,
        #'cids' : [0, 1, 2, 3],
        'cids' : [0],
        'plane_color' : (1., 0., 1.), # purple
        'plane_opacity' : 0.9,
        'gpforce' : gpforce,
        #'itime' : 0,
        'word' : 'Static',
        'model_name' : 'main',
    }
    main_window = ShearMomentTorqueWindow(data)
    main_window.show()
    # Enter the main loop
    app.exec_()


if __name__ == '__main__':   # pragma: no cover
    main()
