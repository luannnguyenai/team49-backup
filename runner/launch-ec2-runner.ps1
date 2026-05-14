[CmdletBinding()]
param(
    [string]$InstanceName = "a20-gha-runner-01",
    [string]$InstanceType = "c7i.xlarge",
    [string]$Region = "ap-southeast-1",
    [string]$KeyName,
    [string]$AllowedSshCidr,
    [string]$InstanceProfileName = "",
    [string]$SubnetId = "",
    [string]$VpcId = "",
    [int]$RootVolumeGiB = 80
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$tfOutputsPath = Join-Path $repoRoot "deploy-ecs\terraform\live\prod\tf-outputs.json"
$userDataPath = Join-Path $PSScriptRoot "user-data.sh"

if (-not (Test-Path $tfOutputsPath)) {
    throw "Missing Terraform outputs file: $tfOutputsPath"
}
if (-not (Test-Path $userDataPath)) {
    throw "Missing user-data file: $userDataPath"
}
if (-not $KeyName) {
    throw "KeyName is required."
}

$tf = Get-Content $tfOutputsPath -Raw | ConvertFrom-Json
if (-not $VpcId) {
    $VpcId = $tf.vpc_id.value
}
if (-not $SubnetId) {
    $SubnetId = $tf.public_subnet_ids.value[0]
}
if (-not $AllowedSshCidr) {
    try {
        $publicIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
        $AllowedSshCidr = "$publicIp/32"
    }
    catch {
        throw "AllowedSshCidr was not provided and public IP detection failed."
    }
}

$amiId = aws ssm get-parameter `
    --region $Region `
    --name "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id" `
    --query "Parameter.Value" `
    --output text

$sgName = "a20-gha-runner-sg"
$sgId = aws ec2 describe-security-groups `
    --region $Region `
    --filters "Name=group-name,Values=$sgName" "Name=vpc-id,Values=$VpcId" `
    --query "SecurityGroups[0].GroupId" `
    --output text

if ($sgId -eq "None" -or [string]::IsNullOrWhiteSpace($sgId)) {
    $sgId = aws ec2 create-security-group `
        --region $Region `
        --group-name $sgName `
        --description "Security group for A20 GitHub Actions runner" `
        --vpc-id $VpcId `
        --query "GroupId" `
        --output text

    aws ec2 authorize-security-group-ingress `
        --region $Region `
        --group-id $sgId `
        --ip-permissions "[{`"IpProtocol`":`"tcp`",`"FromPort`":22,`"ToPort`":22,`"IpRanges`":[{`"CidrIp`":`"$AllowedSshCidr`",`"Description`":`"Operator SSH`"}]}]" | Out-Null
}

$userData = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content $userDataPath -Raw)))
$blockDeviceMappings = "[{`"DeviceName`":`"/dev/sda1`",`"Ebs`":{`"VolumeSize`":$RootVolumeGiB,`"VolumeType`":`"gp3`",`"DeleteOnTermination`":true}}]"
$tagSpecs = "[{`"ResourceType`":`"instance`",`"Tags`":[{`"Key`":`"Name`",`"Value`":`"$InstanceName`"},{`"Key`":`"ManagedBy`",`"Value`":`"codex`"},{`"Key`":`"Role`",`"Value`":`"github-actions-runner`"}]}]"

$runArgs = @(
    "ec2", "run-instances",
    "--region", $Region,
    "--image-id", $amiId,
    "--instance-type", $InstanceType,
    "--key-name", $KeyName,
    "--subnet-id", $SubnetId,
    "--security-group-ids", $sgId,
    "--associate-public-ip-address",
    "--block-device-mappings", $blockDeviceMappings,
    "--tag-specifications", $tagSpecs,
    "--user-data", $userData,
    "--query", "Instances[0].InstanceId",
    "--output", "text"
)

if ($InstanceProfileName) {
    $runArgs += @("--iam-instance-profile", "Name=$InstanceProfileName")
}

$instanceId = aws @runArgs
aws ec2 wait instance-running --region $Region --instance-ids $instanceId
aws ec2 wait instance-status-ok --region $Region --instance-ids $instanceId

$instanceInfo = aws ec2 describe-instances `
    --region $Region `
    --instance-ids $instanceId `
    --query "Reservations[0].Instances[0].{InstanceId:InstanceId,PublicIp:PublicIpAddress,PrivateIp:PrivateIpAddress,SubnetId:SubnetId,SecurityGroupIds:SecurityGroups[*].GroupId,State:State.Name,InstanceType:InstanceType}" `
    --output json

$instanceInfo
