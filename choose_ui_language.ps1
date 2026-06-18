Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "CZN Auto"
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true
$form.ClientSize = New-Object System.Drawing.Size(360, 150)

function U([int[]]$codes) {
    -join ($codes | ForEach-Object { [char]$_ })
}

$label = New-Object System.Windows.Forms.Label
$label.Text = U @(35831, 36873, 25321, 28216, 25103, 35821, 35328, 65306)
$label.AutoSize = $true
$label.Location = New-Object System.Drawing.Point(24, 24)
$label.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 10)
$form.Controls.Add($label)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = U @(19981, 30830, 23450, 23601, 36873, 8220, 33258, 21160, 8221, 12290)
$hint.AutoSize = $true
$hint.Location = New-Object System.Drawing.Point(24, 52)
$hint.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)
$form.Controls.Add($hint)

function Add-LangButton($text, $value, $x) {
    $button = New-Object System.Windows.Forms.Button
    $button.Text = $text
    $button.Size = New-Object System.Drawing.Size(92, 34)
    $button.Location = New-Object System.Drawing.Point($x, 92)
    $button.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)
    $button.Add_Click({
        $form.Tag = $value
        $form.Close()
    }.GetNewClosure())
    $form.Controls.Add($button)
}

Add-LangButton (U @(33258, 21160)) "auto" 24
Add-LangButton (U @(31616, 20307)) "zh-Hans" 134
Add-LangButton (U @(32321, 20307)) "zh-Hant" 244

$form.Add_Shown({ $form.Activate() })
[void]$form.ShowDialog()

if ([string]::IsNullOrWhiteSpace([string]$form.Tag)) {
    "cancel"
} else {
    [string]$form.Tag
}
