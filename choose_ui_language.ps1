Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "CZN Auto"
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.TopMost = $true
$form.ClientSize = New-Object System.Drawing.Size(520, 220)

function U([int[]]$codes) {
    -join ($codes | ForEach-Object { [char]$_ })
}

$fontNormal = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)
$fontTitle = New-Object System.Drawing.Font("Microsoft YaHei UI", 10)
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$numberStyle = [System.Globalization.NumberStyles]::Float

$label = New-Object System.Windows.Forms.Label
$label.Text = U @(35831, 36873, 25321, 28216, 25103, 35821, 35328, 65306)
$label.AutoSize = $true
$label.Location = New-Object System.Drawing.Point(24, 20)
$label.Font = $fontTitle
$form.Controls.Add($label)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = U @(19981, 30830, 23450, 23601, 36873, 8220, 33258, 21160, 8221, 12290)
$hint.AutoSize = $true
$hint.Location = New-Object System.Drawing.Point(24, 48)
$hint.Font = $fontNormal
$form.Controls.Add($hint)

function Add-Radio($text, $value, $x, $checked) {
    $radio = New-Object System.Windows.Forms.RadioButton
    $radio.Text = $text
    $radio.Tag = $value
    $radio.Size = New-Object System.Drawing.Size(95, 26)
    $radio.Location = New-Object System.Drawing.Point($x, 74)
    $radio.Font = $fontNormal
    $radio.Checked = $checked
    $form.Controls.Add($radio)
    return $radio
}

$autoRadio = Add-Radio (U @(33258, 21160)) "auto" 24 $true
$simpRadio = Add-Radio (U @(31616, 20307)) "zh-Hans" 130 $false
$tradRadio = Add-Radio (U @(32321, 20307)) "zh-Hant" 236 $false

$rewardLabel = New-Object System.Windows.Forms.Label
$rewardLabel.Text = U @(22870, 21169, 19977, 36873, 19968, 31561, 24453, 40, 31186, 41, 58)
$rewardLabel.AutoSize = $true
$rewardLabel.Location = New-Object System.Drawing.Point(24, 116)
$rewardLabel.Font = $fontNormal
$form.Controls.Add($rewardLabel)

$rewardBox = New-Object System.Windows.Forms.TextBox
$rewardBox.Text = "1.5"
$rewardBox.Size = New-Object System.Drawing.Size(70, 24)
$rewardBox.Location = New-Object System.Drawing.Point(168, 112)
$rewardBox.Font = $fontNormal
$form.Controls.Add($rewardBox)

$rewardHint = New-Object System.Windows.Forms.Label
$rewardHint.Text = U @(40664, 35748, 32, 49, 46, 53, 12290, 36339, 36807, 26790, 36793, 26102, 21487, 22686, 21152, 31561, 24453, 26102, 38388, 12290)
$rewardHint.AutoSize = $true
$rewardHint.Location = New-Object System.Drawing.Point(250, 116)
$rewardHint.Font = $fontNormal
$form.Controls.Add($rewardHint)

$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = U @(30830, 23450)
$okButton.Size = New-Object System.Drawing.Size(86, 32)
$okButton.Location = New-Object System.Drawing.Point(310, 164)
$okButton.Font = $fontNormal
$okButton.Add_Click({
    $rewardValue = 0.0
    if (-not [double]::TryParse($rewardBox.Text.Trim(), $numberStyle, $culture, [ref]$rewardValue)) {
        [System.Windows.Forms.MessageBox]::Show((U @(25968, 20540, 26684, 24335, 19981, 27491, 30830, 12290)), "CZN Auto") | Out-Null
        return
    }
    if ($rewardValue -lt 0 -or $rewardValue -gt 10) {
        [System.Windows.Forms.MessageBox]::Show((U @(31561, 24453, 24314, 35758, 32, 48, 32, 21040, 32, 49, 48, 32, 31186, 12290)), "CZN Auto") | Out-Null
        return
    }
    $form.Tag = "ok"
    $form.Close()
})
$form.Controls.Add($okButton)

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = U @(21462, 28040)
$cancelButton.Size = New-Object System.Drawing.Size(86, 32)
$cancelButton.Location = New-Object System.Drawing.Point(408, 164)
$cancelButton.Font = $fontNormal
$cancelButton.Add_Click({
    $form.Tag = "cancel"
    $form.Close()
})
$form.Controls.Add($cancelButton)

$form.AcceptButton = $okButton
$form.CancelButton = $cancelButton
$form.Add_Shown({ $form.Activate() })
[void]$form.ShowDialog()

if ([string]$form.Tag -ne "ok") {
    "cancel"
} else {
    if ($simpRadio.Checked) {
        "zh-Hans"
    } elseif ($tradRadio.Checked) {
        "zh-Hant"
    } else {
        "auto"
    }
    ([double]::Parse($rewardBox.Text.Trim(), $culture)).ToString("0.###", $culture)
}
