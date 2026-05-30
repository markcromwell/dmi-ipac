"""
wcac_gui — desktop GUI for the WCAC heat exchanger calculator.

Pure Tkinter (ships with Python) so a single file runs on Windows and macOS
with no extra dependencies. Imports the wcac library directly — the desktop
app keeps the proprietary engine local (no network needed).

Run:
    python -m targets.desktop.wcac_gui

Build a standalone Windows .exe / macOS .app with PyInstaller:
    pyinstaller --onefile --windowed --name DMI-WCAC targets/desktop/wcac_gui.py
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from wcac import calculate, validate, WCACInputs, list_models, Severity
from wcac.calculate import _FLUID_CODE, TUBE_MAT_K

GASES   = [k for k, v in _FLUID_CODE.items() if v.startswith('g')]
LIQUIDS = [k for k, v in _FLUID_CODE.items() if v.startswith('l')]
MATERIALS = list(TUBE_MAT_K.keys())
TUBE_FLOW_UOMS  = ['Scfm', 'Acfm', 'lb/s', 'lb/min', 'lb/h', 'kg/s', 'kg/min', 'kg/h', 'Nm3/h']
SHELL_FLOW_UOMS = ['USgpm', 'litre/min', 'm3/h', 'lb/s', 'lb/min', 'lb/h', 'kg/s', 'kg/min', 'kg/h']

DARK = '#1f2937'; PANEL = '#374151'; ACCENT = '#2563eb'; TEXT = '#f9fafb'


class WCACApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DMI IPAC / WCAC Heat Exchanger Design')
        self.geometry('1000x720')
        self.configure(bg=DARK)
        self._build_styles()
        self._build_ui()
        self._last_result = None
        self._last_inputs = None

    def _build_styles(self):
        s = ttk.Style(self)
        try: s.theme_use('clam')
        except tk.TclError: pass
        s.configure('.', background=DARK, foreground=TEXT, fieldbackground=PANEL)
        s.configure('TLabel', background=DARK, foreground=TEXT)
        s.configure('Head.TLabel', font=('Segoe UI', 13, 'bold'))
        s.configure('Sec.TLabel', font=('Segoe UI', 9, 'bold'), foreground='#9ca3af')
        s.configure('TButton', background=ACCENT, foreground='white',
                    font=('Segoe UI', 10, 'bold'), padding=6)
        s.configure('TEntry', fieldbackground=PANEL, foreground=TEXT)
        s.configure('TCombobox', fieldbackground=PANEL, foreground=TEXT)

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg='#111827', height=56)
        hdr.pack(fill='x')
        tk.Label(hdr, text='DIVERSIFIED MANUFACTURING INC.', bg='#111827',
                 fg='white', font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=16, pady=(8, 0))
        tk.Label(hdr, text='IPAC Air Cooled Heat Exchanger Design Program',
                 bg='#111827', fg='#9ca3af', font=('Segoe UI', 9)).pack(anchor='w', padx=16)

        body = tk.Frame(self, bg=DARK); body.pack(fill='both', expand=True, padx=12, pady=12)
        left = tk.Frame(body, bg=DARK); left.pack(side='left', fill='both', expand=True)
        right = tk.Frame(body, bg=DARK, width=380); right.pack(side='right', fill='both')

        self.vars = {}

        def section(parent, title):
            ttk.Label(parent, text=title, style='Sec.TLabel').pack(anchor='w', pady=(10, 2))
            f = tk.Frame(parent, bg=DARK); f.pack(fill='x')
            return f

        def field(parent, label, key, default, width=12, values=None, col=0):
            cell = tk.Frame(parent, bg=DARK)
            cell.grid(row=0, column=col, sticky='w', padx=4, pady=2)
            ttk.Label(cell, text=label).pack(anchor='w')
            var = tk.StringVar(value=str(default))
            self.vars[key] = var
            if values:
                w = ttk.Combobox(cell, textvariable=var, values=values, width=width, state='readonly')
            else:
                w = ttk.Entry(cell, textvariable=var, width=width)
            w.pack(anchor='w')
            return var

        # ── Configuration ──
        f = section(left, 'AFTERCOOLER CONFIGURATION')
        field(f, 'Model', 'model', 'W0230', values=list_models(), col=0)
        field(f, 'Bundle', 'bundle_type', 'Fixed', values=['Fixed', 'Removable'], col=1)
        field(f, 'Tube type', 'tube_type', 'Std groove', values=['Std groove', 'Plain'], col=2)
        f2 = tk.Frame(left, bg=DARK); f2.pack(fill='x')
        field(f2, 'Tube material', 'tube_material', 'Stainless (S3040*)', width=22, values=MATERIALS, col=0)

        # ── Tube side ──
        f = section(left, 'TUBE SIDE (COMPRESSED GAS)')
        field(f, 'Fluid', 'tube_fluid', 'Air', values=GASES, col=0)
        field(f, 'Pressure (psig)', 'tube_pressure_psig', 150, col=1)
        field(f, 'Temp in (F)', 'tube_temp_in_F', 250, col=2)
        f = tk.Frame(left, bg=DARK); f.pack(fill='x')
        field(f, 'Flow', 'tube_flow', 1423, col=0)
        field(f, 'Flow unit', 'tube_flow_uom', 'Scfm', values=TUBE_FLOW_UOMS, col=1)
        field(f, 'Fouling', 'tube_fouling', 0.0, col=2)

        # ── Shell side ──
        f = section(left, 'SHELL SIDE (COOLING LIQUID)')
        field(f, 'Fluid', 'shell_fluid', 'Water', values=LIQUIDS, col=0)
        field(f, 'Temp in (F)', 'shell_temp_in_F', 70, col=1)
        field(f, 'Glycol %', 'glycol_concentration', 40, col=2)
        f = tk.Frame(left, bg=DARK); f.pack(fill='x')
        field(f, 'Flow', 'shell_flow', 60, col=0)
        field(f, 'Flow unit', 'shell_flow_uom', 'USgpm', values=SHELL_FLOW_UOMS, col=1)
        field(f, 'Fouling', 'shell_fouling', 0.0, col=2)

        # ── Compressor suction ──
        f = section(left, 'COMPRESSOR SUCTION')
        field(f, 'Pressure (psia)', 'suction_pressure_psia', 14.7, col=0)
        field(f, 'Temp (F)', 'suction_temp_F', 85, col=1)
        field(f, 'RH (%)', 'suction_rh_pct', 36, col=2)

        # ── Performance ──
        f = section(left, 'PERFORMANCE')
        field(f, 'Surface area margin (%)', 'surface_area_margin', 0.0, width=10, col=0)

        # ── Buttons ──
        btns = tk.Frame(left, bg=DARK); btns.pack(fill='x', pady=14)
        ttk.Button(btns, text='CALCULATE', command=self.on_calculate).pack(side='left')
        ttk.Button(btns, text='Save Datasheet…', command=self.on_save).pack(side='left', padx=8)

        # ── Results panel ──
        ttk.Label(right, text='RESULTS', style='Sec.TLabel').pack(anchor='w')
        self.results = tk.Text(right, bg=PANEL, fg=TEXT, font=('Consolas', 10),
                               width=46, height=34, relief='flat', wrap='none')
        self.results.pack(fill='both', expand=True, pady=4)
        self.results.insert('1.0', 'Enter inputs and click CALCULATE.')
        self.results.config(state='disabled')

    # ── Logic ──
    def _gather(self) -> WCACInputs:
        def num(k): return float(self.vars[k].get())
        def s(k): return self.vars[k].get()
        return WCACInputs(
            model=s('model'), bundle_type=s('bundle_type'), tube_type=s('tube_type'),
            tube_material=s('tube_material'),
            tube_fluid=s('tube_fluid'), tube_pressure_psig=num('tube_pressure_psig'),
            tube_temp_in_F=num('tube_temp_in_F'), tube_flow=num('tube_flow'),
            tube_flow_uom=s('tube_flow_uom'), tube_fouling=num('tube_fouling'),
            shell_fluid=s('shell_fluid'), shell_temp_in_F=num('shell_temp_in_F'),
            shell_flow=num('shell_flow'), shell_flow_uom=s('shell_flow_uom'),
            shell_fouling=num('shell_fouling'), glycol_concentration=num('glycol_concentration'),
            suction_pressure_psia=num('suction_pressure_psia'),
            suction_temp_F=num('suction_temp_F'), suction_rh_pct=num('suction_rh_pct'),
            surface_area_margin=num('surface_area_margin'),
        )

    def on_calculate(self):
        try:
            inp = self._gather()
        except ValueError:
            messagebox.showerror('Input error', 'All numeric fields must be numbers.')
            return

        issues = validate(inp)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        warnings = [i for i in issues if i.severity is Severity.WARNING]
        if errors:
            messagebox.showerror('Invalid inputs',
                                 '\n'.join(f'• {e.field}: {e.message}' for e in errors))
            return
        if warnings:
            go = messagebox.askokcancel(
                'Warnings',
                '\n'.join(f'• {w.message}' for w in warnings) +
                '\n\nResults may be unreliable. Continue?')
            if not go:
                return

        res = calculate(inp)
        self._last_result = res; self._last_inputs = inp
        self._show(self._format(inp, res))

    def _format(self, inp, r):
        out = []
        out.append(f'Model {inp.model}  ({inp.bundle_type}, {inp.tube_type})')
        out.append('=' * 44)
        rows = [
            ('Total heat',        f'{r.Q_Btu_h:,.0f}', 'Btu/h'),
            ('Tube outlet',       f'{r.tube_out_F:.1f}', 'F'),
            ('Shell outlet',      f'{r.shell_out_F:.1f}', 'F'),
            ('Dew point',         f'{r.dew_point_F:.1f}', 'F'),
            ('Tube dP',           f'{r.dP_tube_psi:.2f}', 'psi'),
            ('Shell dP',          f'{r.dP_shell_psi:.2f}', 'psi'),
            ('Tube Re',           f'{r.tube_Re:,.0f}', ''),
            ('Shell Re',          f'{r.shell_Re:,.0f}', ''),
            ('Tube HTC',          f'{r.tube_HTC_btu:.0f}', 'Btu/h.ft2.R'),
            ('Shell HTC',         f'{r.shell_HTC_btu:.0f}', 'Btu/h.ft2.R'),
            ('Overall U',         f'{r.overall_U_btu:.0f}', 'Btu/h.ft2.R'),
            ('LMTD',              f'{r.LMTD_R:.1f}', 'R'),
            ('Surface area',      f'{r.area_ft2:.1f}', 'ft2'),
            ('Tubes',             f'{r.Nt}', ''),
            ('Condensate',        f'{r.condensate_lb_h:.1f}', 'lb/h'),
            ('Condensing heat',   f'{r.condensing_Btu_h:,.0f}', f'Btu/h ({r.condensing_pct:.1f}%)'),
        ]
        for label, val, unit in rows:
            out.append(f'{label:.<18s} {val:>12s} {unit}')
        out.append('')
        out.append('Tube wall temps (F):')
        out.append('  ' + ', '.join(f'{t:.0f}' for t in r.tube_wall_temps_F))
        return '\n'.join(out)

    def _show(self, text):
        self.results.config(state='normal')
        self.results.delete('1.0', 'end')
        self.results.insert('1.0', text)
        self.results.config(state='disabled')

    def on_save(self):
        if not self._last_result:
            messagebox.showinfo('Nothing to save', 'Calculate first.')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.txt', filetypes=[('Text', '*.txt')],
            initialfile=f'DMI-{self._last_inputs.model}.txt')
        if path:
            # Reuse the CLI datasheet formatter
            from targets.cli.wcac_cli import format_datasheet
            with open(path, 'w', encoding='utf-8') as f:
                f.write(format_datasheet(self._last_inputs, self._last_result))
            messagebox.showinfo('Saved', f'Datasheet written to\n{path}')


def main():
    WCACApp().mainloop()


if __name__ == '__main__':
    main()
