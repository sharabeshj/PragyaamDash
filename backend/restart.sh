kill $(ps aux | grep ssh| grep 8000 | awk '{print$2}')

kubectl delete service backend
kubectl delete deployment backend

docker container prune
docker rmi -f backend:latest

docker build -t backend .

kubectl create -f backend_config.yaml

sleep 5

ip=$(kubectl get services | grep backend | awk '{print $3}')
port=8000   
ssh -o StrictHostKeyChecking=no -i "$HOME"/.minikube/machines/minikube/id_rsa docker@$(minikube ip) -N -T -L 8000:"$ip":"$port" &
