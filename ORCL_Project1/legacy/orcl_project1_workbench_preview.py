"""FIN 439 ORCL Project 1 -- bounded VALUATION workbench PREVIEW, revision 4.

Run in VS Code terminal: py orcl_project1_workbench_preview.py
No third-party packages. Python for Windows typically includes Tkinter.

Controls change WACC/g and balance-sheet treatment only. These are NOT the
required Oracle-specific OPERATING-pro-forma sensitivities, which must await
student's written, AI-off, pre-run locked changed-input prediction. Do not
present this preview as the complete final Project 1 submission.
"""
import copy
import sys

import orcl_project1_post_q1_proforma as proforma
import orcl_project1_valuation_bridge as finance


def basic_smoke():
    rows=proforma.project()
    proforma.audit_independently(rows)
    out=finance.discounted_case(rows,.114,.03)
    return (out["equity_bridge"]["indicative_dollars_per_share_NOT_FINAL"],
            out["dcf"]["terminal_value_share"])


def run_ui():
    import tkinter as tk
    from tkinter import ttk
    root=tk.Tk()
    root.title("Oracle Project 1 - Valuation Workbench Preview [NOT FINAL]")
    root.geometry("1010x730")
    root.minsize(930,650)
    root.configure(bg="#f4f5f7")
    rows=proforma.project()
    proforma.audit_independently(rows)

    bg="#f4f5f7"
    outer=ttk.Frame(root,padding=18)
    outer.pack(fill="both",expand=True)
    header=ttk.Label(outer, text="ORCL  |  Revision 4 Valuation Workbench Preview",
                     font=("Segoe UI",18,"bold"))
    header.pack(anchor="w")
    ttk.Label(outer, text=("Financial statement anchor: Aug 31, 2026 | USD millions | "
                           "Not a final dated investment valuation"),
              font=("Segoe UI",10)).pack(anchor="w",pady=(0,10))
    ttk.Label(outer,text=("Only discount-rate and bridge controls are active. "
                          "Operating-driver tests still require your AI-off pre-run prediction."),
              foreground="#a35d00").pack(anchor="w",pady=(0,12))

    panel=ttk.LabelFrame(outer,text="Bounded valuation inputs and bridge policies",padding=10)
    panel.pack(fill="x",pady=(0,10))
    wc=tk.IntVar(value=114)
    gr=tk.IntVar(value=30)
    cp=tk.StringVar(value="excess")
    pp=tk.StringVar(value="outstanding_claim")
    wlabel=ttk.Label(panel,text="WACC: 11.4%",font=("Segoe UI",10,"bold"))
    wlabel.grid(row=0,column=0,sticky="w")
    glabel=ttk.Label(panel,text="Terminal growth: 3.0%",font=("Segoe UI",10,"bold"))
    glabel.grid(row=0,column=2,sticky="w",padx=(30,0))
    wscale=tk.Scale(panel,from_=104,to=124,orient="horizontal",variable=wc,
                    showvalue=False,resolution=1,length=330,highlightthickness=0)
    wscale.grid(row=1,column=0,columnspan=2,sticky="w")
    gscale=tk.Scale(panel,from_=20,to=40,orient="horizontal",variable=gr,
                    showvalue=False,resolution=1,length=330,highlightthickness=0)
    gscale.grid(row=1,column=2,columnspan=2,sticky="w",padx=(30,0))
    ttk.Label(panel,text="WACC range 10.4-12.4% (legacy illustrative range)").grid(
        row=2,column=0,columnspan=2,sticky="w")
    ttk.Label(panel,text="Growth range 2-4% (not yet evidenced)").grid(
        row=2,column=2,columnspan=2,sticky="w",padx=(30,0))
    ttk.Label(panel,text="Cash in EV/equity bridge:").grid(row=3,column=0,sticky="w",pady=(15,0))
    ttk.Radiobutton(panel,text="Excess above $10B floor",variable=cp,value="excess").grid(
        row=4,column=0,sticky="w")
    ttk.Radiobutton(panel,text="All unrestricted cash",variable=cp,value="total").grid(
        row=5,column=0,sticky="w")
    ttk.Label(panel,text="Convertible preferred treatment:").grid(
        row=3,column=2,sticky="w",padx=(30,0),pady=(15,0))
    ttk.Radiobutton(panel,text="Subtract current $4.954B preferred claim",
                    variable=pp,value="outstanding_claim").grid(row=4,column=2,columnspan=2,sticky="w",padx=(30,0))
    ttk.Radiobutton(panel,text="If-converted illustration (shares +31.238M)",
                    variable=pp,value="if_converted").grid(row=5,column=2,columnspan=2,sticky="w",padx=(30,0))

    output=ttk.LabelFrame(outer,text="Signed FCFF DCF and enterprise-to-common bridge",padding=10)
    output.pack(fill="x",pady=(0,10))
    metric=ttk.Label(output,text="",font=("Segoe UI",16,"bold"))
    metric.pack(anchor="w")
    sub=ttk.Label(output,text="",font=("Consolas",10))
    sub.pack(anchor="w",pady=(5,4))
    warning=ttk.Label(output,text="",foreground="#a12622",wraplength=920)
    warning.pack(anchor="w")
    checks=ttk.Label(outer,text="",font=("Segoe UI",10,"bold"))
    checks.pack(anchor="w",pady=(5,8))
    table=ttk.LabelFrame(outer,text="WACC / g grid (legacy base; indicative dollars per share)",padding=10)
    table.pack(fill="x",pady=(0,10))
    gridlabel=ttk.Label(table,text="",font=("Consolas",10),justify="left")
    gridlabel.pack(anchor="w")
    footer=ttk.Label(outer,text=("WARNINGS: Unnormalized terminal reinvestment; finance/operating leases; "
                                  "customer prepayments; SBC dilution; non-contemporaneous balance-sheet anchor; "
                                  "WACC not verified. Not a recommendation."),
                     foreground="#a35d00",wraplength=915)
    footer.pack(anchor="w",pady=(6,6))
    buttons=ttk.Frame(outer)
    buttons.pack(anchor="w",pady=(5,0))

    def refresh(*args):
        w,g=wc.get()/1000,gr.get()/1000
        wlabel.configure(text=f"WACC: {w*100:.1f}%")
        glabel.configure(text=f"Terminal growth: {g*100:.1f}%")
        try:
            out=finance.discounted_case(rows,w,g,cp.get(),pp.get())
            dcf,br=out["dcf"],out["equity_bridge"]
            metric.configure(text=(f"ILLUSTRATIVE ${br['indicative_dollars_per_share_NOT_FINAL']:,.2f}/share "
                                   f"   |   EV ${dcf['enterprise_value']/1000:,.1f}B"))
            sub.configure(text=(f"PV signed forecast FCFF ${dcf['pv_explicit']/1000:,.2f}B | "
                                f"PV terminal ${dcf['pv_terminal']/1000:,.2f}B | "
                                f"Common shares {br['shares_millions']:,.3f}M | "
                                f"Bridge gap {br['bridge_gap']:.6f}M"))
            pct=dcf['terminal_value_share']*100
            warning.configure(text=(f"High dependency: {pct:.1f}% of enterprise value comes from "
                                    "UNVERIFIED terminal FCFF assumptions." if pct>80
                                    else f"Terminal-value contribution {pct:.1f}%."))
            checks.configure(text="PASS: base pro-forma reconciled; cash/leases/preferred bridge reconciled",
                             foreground="#196b39")
            tab=["WACC \\ g     2.0%       3.0%       4.0%"]
            for w_grid in finance.WACC_GRID:
                results=[finance.discounted_case(rows,w_grid,g_grid,cp.get(),pp.get())
                         ["equity_bridge"]["indicative_dollars_per_share_NOT_FINAL"]
                         for g_grid in finance.G_GRID]
                tab.append(f"{w_grid:>8.1%}   "+"  ".join(f"{v:8.2f}" for v in results))
            gridlabel.configure(text="\n".join(tab))
        except (ValueError,KeyError) as e:
            metric.configure(text="MODEL CHECK FAILED")
            sub.configure(text="A parameter or bridge check failed; reset base before relying on output")
            warning.configure(text=str(e))
            checks.configure(text="FAIL: valuation withheld",foreground="#b4201e")
            gridlabel.configure(text="No grid for an invalid model")

    def reset():
        wc.set(114);gr.set(30);cp.set("excess");pp.set("outstanding_claim")
        refresh()

    def break_demo():
        altered=copy.deepcopy(proforma.OPEN)
        altered["finance_lease_liabilities"]+=1000
        try:
            finance.source_bridge(altered)
            checks.configure(text="ERROR: broken opening was not detected",foreground="#b4201e")
        except ValueError as e:
            checks.configure(text=f"EXPECTED FAIL DETECTED: {e}",foreground="#b4201e")
            warning.configure(text="Demo only: temporary corrupted balance (not saved); click Restore base")

    ttk.Button(buttons,text="Restore base",command=reset).pack(side="left",padx=(0,8))
    ttk.Button(buttons,text="Demo failing check",command=break_demo).pack(side="left")
    for v in (wc,gr,cp,pp):
        v.trace_add("write",refresh)
    refresh()
    root.mainloop()


if __name__=="__main__":
    if "--smoke" in sys.argv:
        value,pct=basic_smoke()
        print(f"GUI computational core PASS: ${value:.2f}/share diagnostic, "
              f"terminal share {pct*100:.1f}%")
    else:
        run_ui()
