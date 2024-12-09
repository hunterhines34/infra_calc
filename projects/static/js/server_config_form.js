function serverConfigForm() {
    return {
        components: {
            rams: window.existingConfig?.rams || [],
            storage: window.existingConfig?.storage || [],
            gpus: window.existingConfig?.gpus || [],
            network_cards: window.existingConfig?.network_cards || [],
            licenses: window.existingConfig?.licenses || []
        },
        totalCost: 0,

        init() {
            console.log('Initializing server config form');
            this.calculateTotal();
        },

        addComponent(type) {
            const typeMap = {
                'storage': 'storage',
                'rams': 'rams',
                'gpus': 'gpus',
                'network_cards': 'network_cards',
                'licenses': 'licenses'
            };
            
            const arrayType = typeMap[type] || type;
            console.log('Adding component:', arrayType);
            
            const newComponent = {
                id: '',
                quantity: 1,
                cost: 0,
                selectedPrice: 0
            };
            
            this.components[arrayType].push(newComponent);
            this.calculateTotal();
        },

        removeComponent(type, index) {
            const typeMap = {
                'storage': 'storage',
                'rams': 'rams',
                'gpus': 'gpus',
                'network_cards': 'network_cards',
                'licenses': 'licenses'
            };
            
            const arrayType = typeMap[type] || type;
            this.components[arrayType].splice(index, 1);
            this.calculateTotal();
        },

        updateCost(type, index, price) {
            setTimeout(() => {
                const component = this.components[type][index];
                if (!component) {
                    console.error('Component not found:', type, index);
                    return;
                }
                
                component.selectedPrice = parseFloat(price || 0);
                component.cost = component.quantity * component.selectedPrice;
                this.calculateTotal();
            }, 0);
        },

        calculateTotal() {
            let total = 0;
            
            // CPU cost
            const cpuSelect = document.querySelector('select[name="cpu"]');
            if (cpuSelect && cpuSelect.selectedOptions[0]) {
                total += parseFloat(cpuSelect.selectedOptions[0].dataset.price || 0);
            }

            // Component costs
            Object.values(this.components).forEach(componentArray => {
                componentArray.forEach(component => {
                    total += parseFloat(component.cost || 0);
                });
            });

            this.totalCost = total.toFixed(2);
            console.log('Total cost:', this.totalCost);
        },

        handleSubmit() {
            this.calculateTotal();
            const form = document.querySelector('form');
            if (form) {
                form.submit();
            } else {
                console.error('Form element not found');
            }
        }
    }
} 