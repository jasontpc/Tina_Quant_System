$taskService = New-Object -ComObject Schedule.Service
$taskService.Connect()
$rootFolder = $taskService.GetFolder('\')

$taskDef = $taskService.NewTask(0)
$taskDef.RegistrationInfo.Description = 'Tina 閒置時智力強化（RTX 4050 閒置8分鐘後自動執行）'

# Idle trigger (type 6)
$idleTrigger = $taskDef.Triggers.Create(6)
$idleTrigger.IdleWaitTimeout = 'PT8M0S'
$idleTrigger.IdleDuration = 'PT8M0S'

# Action
$action = $taskDef.Actions.Create(0)
$action.Path = 'cmd.exe'
$action.Arguments = '/c C:\Users\USER\.openclaw\workspace\Tina_Quant_System\idle_trigger.bat'

$settings = $taskDef.Settings
$settings.AllowStartIfOnBatteries = $true
$settings.StopIfGoingOnBatteries = $false
$settings.StartWhenAvailable = $true
$settings.DisallowStartIfOnBatteries = $false
$settings.IdleSettings.StopOnIdleEnd = $false
$settings.IdleSettings.RestartOnIdle = $false

$principal = $taskDef.Principal
$principal.LogonType = 3
$principal.RunLevel = 1

$rootFolder.RegisterTaskDefinition('Tina_Idle_Evolution', $taskDef, 6, $null, $null, 3, $null)
Write-Output 'OK'