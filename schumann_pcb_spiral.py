"""
7.83 Hz Schumann Resonance — PCB Flat Spiral Coil Designer

Generates a planar spiral coil for both transmit (generator) and receive
modes. Outputs KiCad-compatible footprint files and Gerber-ready SVG.

Planar Spiral Equations:
  1. Wheeler approximation (planar circular):
       L = (mu_0 * N^2 * d_avg * c1) / 2 * [ln(c2/rho) + c3*rho + c4*rho^2]
     where rho = (d_out - d_in) / (d_out + d_in)   (fill ratio)
     For circular: c1=1, c2=2.46, c3=0, c4=0.20

  2. Simplified Wheeler (good for rho < 0.5):
       L = 31.33 * mu_0 * N^2 * a^2 / (8*a + 11*c)
     where a = (r_out + r_in)/2, c = r_out - r_in

  3. Tuning capacitance:  C = 1 / ((2*pi*f)^2 * L)

  4. Trace resistance:  R = rho_cu * total_length / (w * t)
     rho_cu = 1.68e-8 ohm*m, t = 35um (1oz copper)

Usage:
  python schumann_pcb_spiral.py              # design report
  python schumann_pcb_spiral.py --svg        # generate SVG artwork
  python schumann_pcb_spiral.py --kicad      # generate KiCad footprint
  python schumann_pcb_spiral.py --gerber     # generate Gerber-ready files
"""

import math
import argparse

PI = math.pi
MU_0 = 4 * PI * 1e-7
C_LIGHT = 2.998e8
RHO_CU = 1.68e-8   # copper resistivity [ohm*m]

# ---------------------------------------------------------------------------
# Design parameters
# ---------------------------------------------------------------------------
FREQ = 7.83           # Hz
PCB_SIZE = 100.0      # board edge length [mm] (100x100 mm = cheap tier at JLCPCB)
N_TURNS = 50          # number of spiral turns
TRACE_W = 0.3         # trace width [mm]
TRACE_GAP = 0.3       # gap between traces [mm]
COPPER_OZ = 1         # copper weight (1 oz = 35 um)
COPPER_T = 35e-6      # copper thickness [m]
LAYERS = 2            # use both sides of PCB (double spiral)

# Derived geometry
PITCH = TRACE_W + TRACE_GAP  # mm
R_OUTER = (PCB_SIZE / 2) - 2.0  # leave 2mm edge clearance
R_INNER = R_OUTER - N_TURNS * PITCH
if R_INNER < 3.0:
    R_INNER = 3.0
    N_TURNS = int((R_OUTER - R_INNER) / PITCH)

R_AVG = (R_OUTER + R_INNER) / 2  # mm
RADIAL_DEPTH = R_OUTER - R_INNER  # mm


def spiral_points(n_turns, r_inner, r_outer, points_per_turn=72):
    """Generate (x, y) points for an Archimedean spiral."""
    pts = []
    total_angle = n_turns * 2 * PI
    n_points = int(n_turns * points_per_turn)
    for i in range(n_points + 1):
        t = i / n_points
        angle = t * total_angle
        r = r_inner + t * (r_outer - r_inner)
        pts.append((r * math.cos(angle), r * math.sin(angle)))
    return pts


def inductance_wheeler_planar(n, r_avg_m, depth_m):
    """Wheeler approximation for planar circular spiral [H]."""
    a = r_avg_m
    c = depth_m
    return 31.33 * MU_0 * n**2 * a**2 / (8 * a + 11 * c)


def inductance_mohan(n, r_out_m, r_in_m):
    """
    Modified Wheeler / Mohan approximation for planar spiral [H].
    More accurate for higher fill ratios.
    """
    d_avg = (r_out_m + r_in_m)
    rho = (r_out_m - r_in_m) / (r_out_m + r_in_m)
    c1, c2, c3, c4 = 1.0, 2.46, 0.0, 0.20
    if rho < 0.001:
        rho = 0.001
    L = (MU_0 * n**2 * d_avg * c1 / 2) * (math.log(c2 / rho) + c3 * rho + c4 * rho**2)
    return L


def trace_length(n, r_inner_m, r_outer_m):
    """Approximate total trace length for Archimedean spiral [m]."""
    return n * PI * (r_outer_m + r_inner_m)


def trace_resistance(length_m, width_m, thickness_m):
    """DC resistance of copper trace [ohm]."""
    return RHO_CU * length_m / (width_m * thickness_m)


def tuning_cap(freq, L):
    """Required parallel capacitance [F]."""
    return 1.0 / ((2 * PI * freq)**2 * L)


# ---------------------------------------------------------------------------
# Calculations (per layer)
# ---------------------------------------------------------------------------
r_avg_m = R_AVG / 1000
r_out_m = R_OUTER / 1000
r_in_m = R_INNER / 1000
depth_m = RADIAL_DEPTH / 1000
trace_w_m = TRACE_W / 1000

L_wheeler = inductance_wheeler_planar(N_TURNS, r_avg_m, depth_m)
L_mohan = inductance_mohan(N_TURNS, r_out_m, r_in_m)
L_single = L_mohan  # Mohan is more accurate

# Two layers in series (same winding direction) ≈ 4× inductance (mutual coupling)
# Conservative estimate: ~3.5× for tightly coupled double-sided PCB spiral
L_total = L_single * LAYERS**2 * 0.88  # ~3.5x for 2 layers

wire_len_single = trace_length(N_TURNS, r_in_m, r_out_m)
wire_len_total = wire_len_single * LAYERS
R_trace = trace_resistance(wire_len_total, trace_w_m, COPPER_T)
C_tune = tuning_cap(FREQ, L_total)
OMEGA = 2 * PI * FREQ
Q = OMEGA * L_total / R_trace
WAVELENGTH = C_LIGHT / FREQ


def generate_svg(filename='schumann_spiral_pcb.svg'):
    """Generate SVG artwork of the spiral coil PCB."""
    board = PCB_SIZE
    margin = 10
    vw = board + margin * 2
    cx, cy = vw / 2, vw / 2

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vw}" '
                 f'width="{int(vw * 4)}" height="{int(vw * 4)}">')

    # Background (PCB green)
    lines.append(f'<rect x="{margin}" y="{margin}" '
                 f'width="{board}" height="{board}" rx="1.5" '
                 f'fill="#1A5C3A" stroke="#0E3A22" stroke-width="0.5"/>')

    # Solder mask area
    lines.append(f'<rect x="{margin+1}" y="{margin+1}" '
                 f'width="{board-2}" height="{board-2}" rx="1" '
                 f'fill="#1E6B42" stroke="none"/>')

    # Spiral trace (front copper)
    pts = spiral_points(N_TURNS, R_INNER, R_OUTER, points_per_turn=60)
    path_d = 'M ' + ' L '.join(f'{cx + p[0]:.2f},{cy + p[1]:.2f}' for p in pts)
    lines.append(f'<path d="{path_d}" fill="none" stroke="#C67B3A" '
                 f'stroke-width="{TRACE_W}" stroke-linecap="round" opacity="0.9"/>')

    # Center pad
    lines.append(f'<circle cx="{cx}" cy="{cy}" r="2" fill="#C67B3A" opacity="0.8"/>')

    # Mounting holes (4 corners)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        hx = cx + dx * (board / 2 - 4)
        hy = cy + dy * (board / 2 - 4)
        lines.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="1.6" '
                     f'fill="#0E3A22" stroke="#C67B3A" stroke-width="0.4"/>')

    # Connection pads (inner and outer)
    # Outer pad
    ox, oy = pts[-1]
    lines.append(f'<rect x="{cx + ox - 1.5:.1f}" y="{cy + oy - 1:.1f}" '
                 f'width="3" height="2" rx="0.3" fill="#C67B3A"/>')
    lines.append(f'<text x="{cx + ox:.1f}" y="{cy + oy + 5:.1f}" '
                 f'text-anchor="middle" font-size="2.5" fill="#C67B3A" '
                 f'font-family="monospace">OUT</text>')

    # Inner pad
    lines.append(f'<text x="{cx:.1f}" y="{cy + 5:.1f}" '
                 f'text-anchor="middle" font-size="2.5" fill="#C67B3A" '
                 f'font-family="monospace">VIA</text>')

    # Silkscreen labels
    lines.append(f'<text x="{margin + 4}" y="{margin + board - 4}" '
                 f'font-size="3.5" fill="#E8DFD2" font-family="monospace" '
                 f'opacity="0.8">SCHUMANN 7.83Hz</text>')
    lines.append(f'<text x="{margin + 4}" y="{margin + board - 9}" '
                 f'font-size="2.5" fill="#E8DFD2" font-family="monospace" '
                 f'opacity="0.6">{N_TURNS}T / {TRACE_W}mm / L={L_total*1000:.1f}mH</text>')

    lines.append('</svg>')

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))
    return filename


def generate_kicad_footprint(filename='schumann_spiral.kicad_mod'):
    """Generate a KiCad footprint file with the spiral as copper tracks."""
    pts = spiral_points(N_TURNS, R_INNER, R_OUTER, points_per_turn=60)

    lines = []
    lines.append(f'(footprint "Schumann_Spiral_{N_TURNS}T"')
    lines.append(f'  (layer "F.Cu")')
    lines.append(f'  (descr "Schumann 7.83Hz planar spiral coil, {N_TURNS} turns")')

    # Spiral as front copper line segments
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        lines.append(f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
                     f'(layer "F.Cu") (width {TRACE_W}))')

    # Pads
    lines.append(f'  (pad "1" smd rect (at {pts[-1][0]:.3f} {pts[-1][1]:.3f}) '
                 f'(size 2 2) (layers "F.Cu" "F.Paste" "F.Mask"))')
    lines.append(f'  (pad "2" thru_hole circle (at 0 0) '
                 f'(size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))')

    # Silkscreen
    lines.append(f'  (fp_text reference "REF**" (at 0 {-R_OUTER - 3}) '
                 f'(layer "F.SilkS") (effects (font (size 2 2) (thickness 0.3))))')
    lines.append(f'  (fp_text value "Schumann_7.83Hz" (at 0 {R_OUTER + 3}) '
                 f'(layer "F.SilkS") (effects (font (size 2 2) (thickness 0.3))))')

    lines.append(')')

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))
    return filename


def print_report():
    print("=" * 70)
    print("  7.83 Hz SCHUMANN RESONANCE — PCB FLAT SPIRAL DESIGN")
    print("=" * 70)

    print("\n--- PCB SPECIFICATIONS ---")
    print(f"  Board size:           {PCB_SIZE:.0f} x {PCB_SIZE:.0f} mm (standard 10x10 cm)")
    print(f"  Copper layers:        {LAYERS} (front + back, series-connected via)")
    print(f"  Copper weight:        {COPPER_OZ} oz ({COPPER_T*1e6:.0f} µm)")

    print("\n--- SPIRAL GEOMETRY ---")
    print(f"  Turns per layer:      {N_TURNS}")
    print(f"  Total turns:          {N_TURNS * LAYERS}")
    print(f"  Trace width:          {TRACE_W} mm")
    print(f"  Trace gap:            {TRACE_GAP} mm")
    print(f"  Pitch:                {PITCH} mm")
    print(f"  Outer radius:         {R_OUTER:.1f} mm")
    print(f"  Inner radius:         {R_INNER:.1f} mm")
    print(f"  Radial depth:         {RADIAL_DEPTH:.1f} mm")
    print(f"  Avg radius:           {R_AVG:.1f} mm")

    print("\n--- ELECTRICAL PARAMETERS ---")
    print(f"  Inductance (1 layer): {L_single*1e6:.1f} µH  ({L_single*1000:.4f} mH)")
    print(f"  Inductance (2-layer): {L_total*1e6:.1f} µH  ({L_total*1000:.4f} mH)")
    print(f"  Trace length (total): {wire_len_total:.2f} m")
    print(f"  DC resistance:        {R_trace:.2f} ohm")
    print(f"  Tuning capacitance:   {C_tune*1e6:.1f} µF")
    print(f"  Q factor:             {Q:.4f}")

    print("\n--- COMPARISON: PCB SPIRAL vs WOUND COIL ---")
    L_wound = 0.4801  # our wound coil
    print(f"  Wound coil L:         480.1 mH  (1000 turns, 150mm radius)")
    print(f"  PCB spiral L:         {L_total*1000:.2f} mH  ({N_TURNS*LAYERS} turns, flat)")
    ratio = L_wound / L_total
    print(f"  Ratio:                {ratio:.0f}× less inductance in PCB")
    print(f"  PCB cap needed:       {C_tune*1e6:.1f} µF (vs 860 µF for wound coil)")

    print("\n--- MODE: GENERATOR (like FG-300) ---")
    print(f"  Drive the spiral with a microcontroller (Arduino/ESP32)")
    print(f"  Generate 7.83 Hz square or sine wave into the coil")
    print(f"  Use H-bridge driver (L298N) for higher current")
    print(f"  Effective range: ~1-3 metres (room-scale)")

    print("\n--- MODE: RECEIVER ---")
    print(f"  Connect tuning cap ({C_tune*1e6:.1f} µF) in parallel")
    print(f"  Feed into preamp (INA217, 60-80 dB gain)")
    print(f"  Sensitivity is lower than wound coil ({ratio:.0f}× less)")
    print(f"  Best for local/strong signal detection")

    print("\n--- ORDERING (JLCPCB / PCBWay) ---")
    print(f"  Board size:     100 x 100 mm")
    print(f"  Layers:         2")
    print(f"  Copper:         1 oz")
    print(f"  Min trace/gap:  {TRACE_W}/{TRACE_GAP} mm")
    print(f"  Finish:         HASL or ENIG")
    print(f"  Qty 5 boards:   ~$2-5 USD")
    print("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Schumann PCB spiral designer')
    parser.add_argument('--svg', action='store_true', help='Generate SVG artwork')
    parser.add_argument('--kicad', action='store_true', help='Generate KiCad footprint')
    args = parser.parse_args()

    print_report()

    if args.svg:
        f = generate_svg()
        print(f"\n  SVG written: {f}")

    if args.kicad:
        f = generate_kicad_footprint()
        print(f"\n  KiCad footprint written: {f}")
