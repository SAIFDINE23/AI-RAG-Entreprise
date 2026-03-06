# 🚀 Déploiement AWS — Terraform + Ansible

Déploie l'application **Enterprise RAG Assistant** sur AWS EC2 avec K3s + ArgoCD.

---

## 📋 Prérequis

- ✅ Compte AWS configuré (`aws configure`)
- ✅ Terraform installé
- ✅ Ansible installé
- ✅ Variables d'environnement pour les clés API :

```bash
export GOOGLE_API_KEY="ta_vraie_clé_google"
export GROQ_API_KEY="ta_vraie_clé_groq"
```

---

## 🏗️ Étape 1 : Provisionner l'infrastructure avec Terraform

```bash
cd terraform

# Initialiser Terraform
terraform init

# Voir ce qui sera créé
terraform plan

# Créer l'infrastructure (EC2 t3.small, VPC, Security Group...)
terraform apply
```

**⚠️ Coût** : ~0.02 €/heure (~0.50 €/jour)

Terraform va créer :
- ✅ VPC + Subnet + Internet Gateway
- ✅ Security Group (ports 22, 80, 443, 8080, 6443)
- ✅ EC2 `t3.small` (Ubuntu 24.04, 2 Go RAM)
- ✅ Elastic IP publique
- ✅ Clé SSH (`rag-assistant-key.pem`)
- ✅ Inventaire Ansible (`../ansible/inventory.ini`)

À la fin, Terraform affiche :
```
Outputs:

ec2_public_ip = "54.xxx.xxx.xxx"
ssh_command = "ssh -i rag-assistant-key.pem ubuntu@54.xxx.xxx.xxx"
argocd_url = "http://54.xxx.xxx.xxx:8080"
app_url = "http://54.xxx.xxx.xxx:30080"
ansible_command = "cd ../ansible && ansible-playbook -i inventory.ini playbook.yml"
```

---

## 🤖 Étape 2 : Déployer l'application avec Ansible

**Exporte d'abord tes clés API** :

```bash
export GOOGLE_API_KEY="AIzaSy..."
export GROQ_API_KEY="gsk_..."
```

Puis lance Ansible :

```bash
cd ../ansible

# Lancer le playbook (prend ~5-10 minutes)
ansible-playbook -i inventory.ini playbook.yml
```

Ansible va :
- ✅ Configurer le swap (1 Go)
- ✅ Installer K3s
- ✅ Installer ArgoCD
- ✅ Construire l'image Docker
- ✅ Déployer l'app RAG sur K3s
- ✅ Exposer l'app sur le port 30080

À la fin, Ansible affiche :
```
╔══════════════════════════════════════════════════════╗
║   DÉPLOIEMENT RÉUSSI ✅                              ║
╚══════════════════════════════════════════════════════╝

🌐 Application RAG: http://54.xxx.xxx.xxx:30080/static/index.html
🔧 ArgoCD UI: https://54.xxx.xxx.xxx:8080
   └─ User: admin
   └─ Pass: xxxxxxxxx

📝 SSH: ssh -i ../terraform/rag-assistant-key.pem ubuntu@54.xxx.xxx.xxx
```

---

## 🧪 Étape 3 : Tester l'application

### Web UI
Ouvre dans ton navigateur :
```
http://<EC2_IP>:30080/static/index.html
```

### ArgoCD UI
```
https://<EC2_IP>:8080
User: admin
Pass: <affiché par Ansible>
```

### SSH
```bash
ssh -i terraform/rag-assistant-key.pem ubuntu@<EC2_IP>

# Voir les pods
kubectl get pods -n rag-assistant

# Logs de l'app
kubectl logs -n rag-assistant -l app.kubernetes.io/name=rag-assistant
```

---

## 💰 Étape 4 : Détruire l'infrastructure (important !)

**Pour arrêter la facturation AWS** :

```bash
cd terraform
terraform destroy
```

Cela supprime :
- ✅ EC2 instance
- ✅ Elastic IP
- ✅ Security Group
- ✅ VPC / Subnet / IGW
- ✅ Clé SSH

**Coût estimé** si tu `destroy` après 2h de test : **~0.04 €**

---

## 📝 Fichiers générés (à NE PAS commit)

```
terraform/
  ├── rag-assistant-key.pem  ← Clé SSH privée
  ├── terraform.tfstate       ← État Terraform
  └── .terraform/             ← Modules Terraform

ansible/
  └── inventory.ini           ← Généré par Terraform
```

Tous exclus par `.gitignore`.

---

## 🔒 Sécurité

- ✅ Clés API passées via variables d'environnement (jamais hardcodées)
- ✅ Clé SSH auto-générée par Terraform
- ✅ Security Group limité aux ports nécessaires
- ✅ Application tourne avec utilisateur non-root (UID 1000)
- ✅ K8s securityContext (readOnlyRootFilesystem, drop ALL capabilities)

---

## 🚨 Important

**APRÈS avoir testé, pense à :**
1. ✅ `terraform destroy` pour éviter les frais
2. ✅ Révoquer tes clés AWS IAM si tu les as partagées
3. ✅ Supprimer les snapshots/volumes EBS orphelins dans la console AWS

---

## 📚 Architecture déployée

```
┌────────────────────────────────────────────┐
│  AWS EC2 t3.small (Ubuntu 24.04, 2 Go)    │
│  ┌──────────────────────────────────────┐ │
│  │  K3s (Kubernetes léger)              │ │
│  │  ┌────────────────┐ ┌──────────────┐│ │
│  │  │ ArgoCD         │ │ RAG App      ││ │
│  │  │ (Port 8080)    │ │ (Port 30080) ││ │
│  │  └────────────────┘ └──────────────┘│ │
│  └──────────────────────────────────────┘ │
│  IP publique : 54.xxx.xxx.xxx             │
└────────────────────────────────────────────┘
         ↑
         │ Terraform provisionne
         │ Ansible configure
```
