VPC_STACK=etl-vpc
DB_STACK=etl-database
COMPUTE_STACK=etl-compute
STORAGE_STACK=etl-storage
API_STACK=etl-api
REGION=af-south-1
S3_BUCKET=etl-bucket-smart-data-manager--2025-12-10-1
LAMBDA_KEY=lambda_package.zip
API_PACKAGE_NAME ?= api_package.zip
API_BUILD_DIR := .api_build
ETL_BUILD_DIR := .etl_build


# AWS CLOUD DEPLOYMENT COMMANDS
deploy-storage:
	aws cloudformation deploy \
		--template-file storage.yml \
		--stack-name $(STORAGE_STACK) \
		--region $(REGION) \
		--profile sdm \
		--parameter-overrides BucketName=$(S3_BUCKET)

deploy-vpc:
	aws cloudformation deploy \
		--template-file vpc.yml \
		--stack-name $(VPC_STACK) \
		--region $(REGION) \
		--profile sdm \
		--capabilities CAPABILITY_NAMED_IAM

deploy-db:
	aws cloudformation deploy \
		--template-file database.yml \
		--stack-name $(DB_STACK) \
		--region $(REGION) \
		--profile sdm \
		--parameter-overrides DBPassword=$(DB_PASSWORD) \
		--capabilities CAPABILITY_NAMED_IAM

deploy-compute:
	aws cloudformation deploy \
		--template-file compute.yml \
		--stack-name $(COMPUTE_STACK) \
		--region $(REGION) \
		--profile sdm \
		--parameter-overrides \
			LambdaS3Bucket=$(shell aws cloudformation list-exports --query "Exports[?Name=='ETL-Lambda-Bucket'].Value" --output text --profile sdm) \
			LambdaS3Key=$(LAMBDA_KEY) \
			RDSHost=$(shell aws cloudformation list-exports --query "Exports[?Name=='ETL-RDS-Endpoint'].Value" --output text --profile sdm) \
			RDSPort=$(shell aws cloudformation list-exports --query "Exports[?Name=='ETL-RDS-Port'].Value" --output text --profile sdm) \
			RDSPassword=$(DB_PASSWORD) \
		--capabilities CAPABILITY_NAMED_IAM

package-etl:
	@echo "==> Cleaning old build dir..."
	rm -rf .etl_build
	mkdir -p .etl_build
	@echo "==> Installing Python dependencies into .etl_build..."
	pip install -r ../smart_data_manager_package/requirements.txt --target .etl_build
	@echo "==> Copying ETL source, excluding MSSQL engine..."
	rsync -av --exclude 'db.py' ../smart_data_manager_package/ .etl_build/
	@echo "==> Creating zip package at project root..."
	cd .etl_build && zip -r ../../lambda_package.zip . -x '*.pyc' -x '__pycache__/*'
	@echo "ETL package created: ../lambda_package.zip"

upload-lambda:
	aws s3 cp ../lambda_package.zip s3://$(S3_BUCKET)/$(LAMBDA_KEY) --profile sdm

package-api:
	@echo "==> Cleaning old build dir..."
	rm -rf $(API_BUILD_DIR)
	@echo "==> Creating build dir $(API_BUILD_DIR)..."
	mkdir -p $(API_BUILD_DIR)
	@echo "==> Installing Python dependencies into $(API_BUILD_DIR)..."
	pip install -r api/requirements.txt --target $(API_BUILD_DIR)
	@echo "==> Copying API source files..."
	cp api/api_handler.py $(API_BUILD_DIR)/
	# (copy any other modules you need)
	@echo "==> Creating zip at project root: ../$(API_PACKAGE_NAME) ..."
	cd $(API_BUILD_DIR) && zip -r ../../$(API_PACKAGE_NAME) ./*


upload-api:
	@echo "Uploading $(API_PACKAGE_NAME) to S3..."
	aws s3 cp ../$(API_PACKAGE_NAME) s3://$(S3_BUCKET)/lambda_api_package.zip
	@echo "Cleaning up..."
	rm -rf /tmp/api_build
	@echo "API package uploaded successfully."


deploy-api:
	aws cloudformation deploy \
		--template-file api.yml \
		--stack-name $(API_STACK) \
		--region $(REGION) \
		--profile sdm \
		--parameter-overrides \
			LambdaS3Bucket=$(S3_BUCKET) \
			LambdaS3Key=lambda_package.zip \
			RDSHost=$(shell aws cloudformation list-exports --query "Exports[?Name=='ETL-RDS-Endpoint'].Value" --output text --profile sdm) \
			RDSPort=$(shell aws cloudformation list-exports --query "Exports[?Name=='ETL-RDS-Port'].Value" --output text --profile sdm) \
			RDSPassword=$(DB_PASSWORD) \
			PowerAppsApiKey=$(POWERAPPS_KEY) \
    		PowerBiApiKey=$(POWERBI_KEY) \
		--capabilities CAPABILITY_NAMED_IAM

delete-all:
	aws cloudformation delete-stack --stack-name $(COMPUTE_STACK)
	aws cloudformation delete-stack --stack-name $(STORAGE_STACK)
	aws cloudformation delete-stack --stack-name $(DB_STACK)
	aws cloudformation delete-stack --stack-name $(VPC_STACK)
	aws cloudformation delete-stack --stack-name $(API_STACK)
 
 
