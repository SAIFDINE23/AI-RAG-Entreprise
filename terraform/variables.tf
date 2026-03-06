# ============================================================
# Terraform Variables
# ============================================================

variable "aws_region" {
  description = "Région AWS pour le déploiement"
  type        = string
  default     = "eu-west-3" # Paris
}

variable "project_name" {
  description = "Nom du projet (utilisé pour les tags et noms de ressources)"
  type        = string
  default     = "rag-assistant"
}

variable "instance_type" {
  description = "Type d'instance EC2 (t3.small = 2 Go RAM, ~0.02€/h)"
  type        = string
  default     = "t3.small"
}
