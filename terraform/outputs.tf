# ============================================================
# Terraform Outputs
# ============================================================

output "ec2_public_ip" {
  description = "Adresse IP publique de l'instance EC2"
  value       = aws_eip.rag_assistant.public_ip
}

output "ec2_instance_id" {
  description = "ID de l'instance EC2"
  value       = aws_instance.rag_assistant.id
}

output "ssh_command" {
  description = "Commande SSH pour se connecter à l'instance"
  value       = "ssh -i ${local_file.private_key.filename} ubuntu@${aws_eip.rag_assistant.public_ip}"
}

output "argocd_url" {
  description = "URL d'ArgoCD une fois déployé"
  value       = "http://${aws_eip.rag_assistant.public_ip}:30443"
}

output "app_url" {
  description = "URL de l'application RAG une fois déployée"
  value       = "http://${aws_eip.rag_assistant.public_ip}:30080/static/index.html"
}

output "ansible_command" {
  description = "Commande pour lancer Ansible"
  value       = "cd ../ansible && ansible-playbook -i inventory.ini playbook.yml"
}
