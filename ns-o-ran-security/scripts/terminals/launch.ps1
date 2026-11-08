# ns-O-RAN launcher - replays the exact window rectangles captured from manual layout.
# C(ns-3) left-full / A(e2term) top-right / B(xApp) bottom-right
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WM {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int m);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int ht,bool repaint);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  static List<IntPtr> _list;
  static bool Collect(IntPtr h, IntPtr p) {
    if (!IsWindowVisible(h)) return true;
    var cn = new StringBuilder(256); GetClassName(h, cn, 256);
    string c = cn.ToString();
    if (c == "CASCADIA_HOSTING_WINDOW_CLASS" || c == "ConsoleWindowClass") _list.Add(h);
    return true;
  }
  public static IntPtr[] TermWindows() {
    _list = new List<IntPtr>();
    EnumWindows(new EnumProc(Collect), IntPtr.Zero);
    return _list.ToArray();
  }
}
"@

# exact rects captured from the manual layout: x,y,w,h
$rects = @{
  C = @(-6,    0,   1389, 1110)
  A = @(1370,  0,   1389, 558)
  B = @(1370,  552, 1389, 558)
}

function Launch-Place($script, $r) {
  $before = [System.Collections.Generic.HashSet[IntPtr]]::new()
  foreach ($h in [WM]::TermWindows()) { [void]$before.Add($h) }
  Start-Process wsl.exe -ArgumentList @('-d','Ubuntu-22.04','--','bash','-lic',$script) | Out-Null
  $new = [IntPtr]::Zero
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 300
    foreach ($h in [WM]::TermWindows()) {
      if (-not $before.Contains($h)) { $new = $h; break }
    }
    if ($new -ne [IntPtr]::Zero) { break }
  }
  if ($new -ne [IntPtr]::Zero) {
    Start-Sleep -Milliseconds 400
    [void][WM]::MoveWindow($new, $r[0], $r[1], $r[2], $r[3], $true)
  }
  return $new
}

$hc = Launch-Place '~/nsoran-term/c.sh' $rects.C
$ha = Launch-Place '~/nsoran-term/a.sh' $rects.A
$hb = Launch-Place '~/nsoran-term/b.sh' $rects.B

if ($hc -ne [IntPtr]::Zero) { [void][WM]::SetForegroundWindow($hc) }
